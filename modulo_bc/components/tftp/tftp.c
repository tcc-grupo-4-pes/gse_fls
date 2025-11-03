#include "tftp.h"
#include "storage.h" // open_temp_file, FIRMWARE_MOUNT_POINT
#include "state_machine/fsm.h" // upload_failure_count

#include <stdio.h>  // FILE operations
#include <string.h> // strstr, memcpy
#include <errno.h>  // errno
#include <stdlib.h> // malloc, free

#include "esp_log.h"
#include "esp_spiffs.h"   // esp_spiffs_info
#include "lwip/sockets.h" // sendto, recvfrom, setsockopt
#include "mbedtls/sha256.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h" // vTaskDelay

static const char *TAG = "tftp";

void handle_rrq(int sock, struct sockaddr_in *client, char *filename)
{
    ESP_LOGI(TAG, "Read Request(GSE requisita): %s", filename);

    if (strstr(filename, ".LUI") == NULL)
    {
        ESP_LOGW(TAG, "Arquivo requisitado não e .LUI");
        return;
    }

    // Cria socket efêmero para transferência (protocolo TFTP padrão)
    int transfer_sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (transfer_sock < 0)
    {
        ESP_LOGE(TAG, "Erro ao criar socket de transferência: errno=%d", errno);
        return;
    }

    // Bind em porta efêmera (porta 0 = sistema escolhe)
    struct sockaddr_in transfer_addr;
    memset(&transfer_addr, 0, sizeof(transfer_addr));
    transfer_addr.sin_family = AF_INET;
    transfer_addr.sin_port = htons(0); // Porta efêmera
    transfer_addr.sin_addr.s_addr = htonl(INADDR_ANY);

    if (bind(transfer_sock, (struct sockaddr *)&transfer_addr, sizeof(transfer_addr)) < 0)
    {
        ESP_LOGE(TAG, "Erro no bind do socket de transferência: errno=%d", errno);
        close(transfer_sock);
        return;
    }

    // Obtém a porta efêmera atribuída
    socklen_t addr_len = sizeof(transfer_addr);
    getsockname(transfer_sock, (struct sockaddr *)&transfer_addr, &addr_len);
    ESP_LOGI(TAG, "Socket de transferência criado na porta %d (TID)", ntohs(transfer_addr.sin_port));

    lui_data_t lui;
    if (init_lui(&lui, ARINC_STATUS_OP_ACCEPTED_NOT_STARTED, "Operation Accepted") != 0)
    {
        ESP_LOGE(TAG, "Falha ao inicializar LUI");
        close(transfer_sock);
        return;
    }

    size_t total_size = sizeof(lui_data_t);
    uint8_t *lui_buf = (uint8_t *)&lui; // Usa ponteiro direto para a estrutura no stack

    int sent = 0;
    uint16_t block = 1;
    int retry_count = 0;

    while (sent < total_size)
    {
        tftp_packet_t pkt;
        pkt.opcode = htons(OP_DATA);
        pkt.data.block = htons(block);

        int chunk = (total_size - sent) < BLOCK_SIZE ? (total_size - sent) : BLOCK_SIZE;
        memcpy(pkt.data.data, (uint8_t *)lui_buf + sent, chunk);

        // Envia do socket efêmero para o cliente
        ssize_t s = sendto(transfer_sock, &pkt, 4 + chunk, 0,
                           (struct sockaddr *)client, sizeof(*client));
        if (s < 0)
        {
            ESP_LOGW(TAG, "Falha ao enviar bloco %d, tentando novamente", block);
            retry_count++;
            upload_failure_count++;

            if (retry_count >= TFTP_RETRY_LIMIT)
            {
                ESP_LOGE(TAG, "Limite de tentativas atingido para bloco %d", block);
                break;
            }
            vTaskDelay(pdMS_TO_TICKS(TFTP_TIMEOUT_SEC * 1000));
            continue;
        }
        ESP_LOGI(TAG, "Enviado bloco %d (%d bytes)", block, chunk);
        retry_count = 0;

        struct timeval tv;
        tv.tv_sec = TFTP_TIMEOUT_SEC;
        tv.tv_usec = 0;
        setsockopt(transfer_sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

        tftp_packet_t ack;
        struct sockaddr_in ack_addr;
        socklen_t ack_len = sizeof(ack_addr);

        ssize_t n = recvfrom(transfer_sock, &ack, sizeof(ack), 0,
                             (struct sockaddr *)&ack_addr, &ack_len);

        if (n > 0 && ntohs(ack.opcode) == OP_ACK && ntohs(ack.block) == block)
        {
            ESP_LOGI(TAG, "ACK recebido para bloco %d", block);
            sent += chunk;
            block++;
        }
        else
        {
            ESP_LOGW(TAG, "ACK nao recebido ou invalido, reenviando bloco %d...", block);
        }

        if (chunk < BLOCK_SIZE)
            break;
    }

    close(transfer_sock);
    ESP_LOGI(TAG, "RRQ concluido, socket de transferência fechado");
}

void handle_wrq(int sock, struct sockaddr_in *client, char *filename, lur_data_t *lur_file)
{
    ESP_LOGI(TAG, "Write Request (GSE envia): %s", filename);

    if (strstr(filename, ".LUR") == NULL)
    {
        ESP_LOGW(TAG, "Arquivo recebido nao e .LUR");
        return;
    }

    // Cria socket efêmero para transferência (protocolo TFTP padrão)
    int transfer_sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (transfer_sock < 0)
    {
        ESP_LOGE(TAG, "Erro ao criar socket de transferência: errno=%d", errno);
        return;
    }

    // Bind em porta efêmera
    struct sockaddr_in transfer_addr;
    memset(&transfer_addr, 0, sizeof(transfer_addr));
    transfer_addr.sin_family = AF_INET;
    transfer_addr.sin_port = htons(0); // Porta efêmera
    transfer_addr.sin_addr.s_addr = htonl(INADDR_ANY);

    if (bind(transfer_sock, (struct sockaddr *)&transfer_addr, sizeof(transfer_addr)) < 0)
    {
        ESP_LOGE(TAG, "Erro no bind do socket de transferência: errno=%d", errno);
        close(transfer_sock);
        return;
    }

    // Obtém a porta efêmera atribuída
    socklen_t addr_len = sizeof(transfer_addr);
    getsockname(transfer_sock, (struct sockaddr *)&transfer_addr, &addr_len);
    ESP_LOGI(TAG, "Socket de transferência criado na porta %d (TID)", ntohs(transfer_addr.sin_port));

    // Envia ACK(0) do socket efêmero para o cliente
    tftp_packet_t ack;
    ack.opcode = htons(OP_ACK);
    ack.block = htons(0);
    sendto(transfer_sock, &ack, 4, 0, (struct sockaddr *)client, sizeof(*client));

    struct timeval tv;
    tv.tv_sec = TFTP_TIMEOUT_SEC;
    tv.tv_usec = 0;
    setsockopt(transfer_sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

    uint16_t expected_block = 1;
    tftp_packet_t pkt;
    struct sockaddr_in recv_addr;
    socklen_t recv_len = sizeof(recv_addr);

    uint8_t lur_buf[256];
    size_t total_received = 0;

    while (1)
    {
        ssize_t n = recvfrom(transfer_sock, &pkt, sizeof(pkt), 0,
                             (struct sockaddr *)&recv_addr, &recv_len);
        if (n < 0)
        {
            ESP_LOGW(TAG, "Timeout ou erro no recebimento (errno=%d)", errno);
            break;
        }

        if (ntohs(pkt.opcode) != OP_DATA || ntohs(pkt.data.block) != expected_block)
        {
            ESP_LOGW(TAG, "Pacote inesperado (opcode=%d, block=%d)",
                     ntohs(pkt.opcode), ntohs(pkt.data.block));
            upload_failure_count++;
            continue;
        }

        int data_len = n - 4;
        if (total_received + data_len <= sizeof(lur_buf))
        {
            memcpy(lur_buf + total_received, pkt.data.data, data_len);
            total_received += data_len;
        }

        ack.opcode = htons(OP_ACK);
        ack.block = htons(expected_block);
        sendto(transfer_sock, &ack, 4, 0, (struct sockaddr *)client, sizeof(*client));

        ESP_LOGI(TAG, "Bloco %d recebido (%d bytes)", expected_block, data_len);
        expected_block++;

        if (data_len < BLOCK_SIZE)
            break; // Ultimo bloco
    }

    if (total_received == 0)
    {
        ESP_LOGW(TAG, "Nenhum dado .LUR recebido");
        close(transfer_sock);
        return;
    }

    // parse LUR using arinc helper
    if (parse_lur(lur_buf, total_received, lur_file) != 0)
    {
        ESP_LOGE(TAG, "Falha ao parsear LUR");
        close(transfer_sock);
        return;
    }

    ESP_LOGI(TAG, "LUR recebido e processado da RAM:");
    ESP_LOGI(TAG, "  File length: %lu", ntohl(lur_file->file_length));
    ESP_LOGI(TAG, "  Protocol version: %s", lur_file->protocol_version);
    ESP_LOGI(TAG, "  Header file name: %s", lur_file->header_filename);
    ESP_LOGI(TAG, "  Load Part Number: %s", lur_file->load_part_number);

    close(transfer_sock);
    ESP_LOGI(TAG, "WRQ concluido, socket de transferência fechado");
}

void make_wrq(int sock, struct sockaddr_in *client_addr, const char *lus_filename, const lus_data_t *lus_data)
{
    ESP_LOGI(TAG, "Iniciando WRQ para envio de %s", lus_filename);

    // Envia WRQ do socket principal (porta 69)
    tftp_packet_t wrq;
    wrq.opcode = htons(OP_WRQ);
    snprintf(wrq.request, sizeof(wrq.request), "%s%coctet%c", lus_filename, 0, 0);

    if (sendto(sock, &wrq, strlen(lus_filename) + 8, 0,
               (struct sockaddr *)client_addr, sizeof(*client_addr)) < 0)
    {
        ESP_LOGE(TAG, "Erro ao enviar WRQ: errno=%d", errno);
        return;
    }

    // Aguarda ACK(0) que virá da porta efêmera do cliente
    tftp_packet_t ack;
    struct sockaddr_in ack_addr;
    socklen_t ack_len = sizeof(ack_addr);

    if (recvfrom(sock, &ack, sizeof(ack), 0,
                 (struct sockaddr *)&ack_addr, &ack_len) < 0)
    {
        ESP_LOGE(TAG, "Erro ao receber ACK inicial: errno=%d", errno);
        return;
    }

    if (ntohs(ack.opcode) != OP_ACK || ntohs(ack.block) != 0)
    {
        ESP_LOGE(TAG, "ACK inicial invalido");
        return;
    }

    // Cliente mudou para porta efêmera, salva o novo endereço
    ESP_LOGI(TAG, "Cliente mudou para TID (porta) %d", ntohs(ack_addr.sin_port));

    // Envia dados para a porta efêmera do cliente
    tftp_packet_t data_pkt;
    data_pkt.opcode = htons(OP_DATA);
    data_pkt.data.block = htons(1);
    memcpy(data_pkt.data.data, lus_data, sizeof(lus_data_t));

    if (sendto(sock, &data_pkt, 4 + sizeof(lus_data_t), 0,
               (struct sockaddr *)&ack_addr, sizeof(ack_addr)) < 0)
    {
        ESP_LOGE(TAG, "Erro ao enviar dados LUS: errno=%d", errno);
        return;
    }

    if (recvfrom(sock, &ack, sizeof(ack), 0,
                 (struct sockaddr *)&ack_addr, &ack_len) < 0)
    {
        ESP_LOGE(TAG, "Erro ao receber ACK final: errno=%d", errno);
        return;
    }

    if (ntohs(ack.opcode) != OP_ACK || ntohs(ack.block) != 1)
    {
        ESP_LOGE(TAG, "ACK final invalido");
        return;
    }

    ESP_LOGI(TAG, "Arquivo LUS enviado com sucesso");
}

void make_rrq(int sock, struct sockaddr_in *client_addr, const char *filename, unsigned char *hash)
{
    ESP_LOGI(TAG, "Iniciando RRQ para %s", filename);

    FILE *temp_file = open_temp_file();
    if (!temp_file)
    {
        ESP_LOGE(TAG, "Failed to open temporary file for write");
        return;
    }

    // Envia RRQ do socket principal (porta 69)
    tftp_packet_t rrq;
    rrq.opcode = htons(OP_RRQ);
    snprintf(rrq.request, sizeof(rrq.request), "%s%coctet%c", filename, 0, 0);

    if (sendto(sock, &rrq, strlen(filename) + 8, 0,
               (struct sockaddr *)client_addr, sizeof(*client_addr)) < 0)
    {
        ESP_LOGE(TAG, "Erro ao enviar RRQ: errno=%d", errno);
        fclose(temp_file);
        return;
    }

    mbedtls_sha256_context sha_ctx;
    mbedtls_sha256_init(&sha_ctx);
    mbedtls_sha256_starts(&sha_ctx, 0);

    size_t total_bytes = 0;
    struct sockaddr_in server_tid_addr; // Porta efêmera do servidor (GSE)
    int first_packet = 1;

    while (1)
    {
        tftp_packet_t data_pkt;
        struct sockaddr_in data_addr;
        socklen_t addr_len = sizeof(data_addr);

        ssize_t n = recvfrom(sock, &data_pkt, sizeof(data_pkt), 0,
                             (struct sockaddr *)&data_addr, &addr_len);
        if (n < 0)
        {
            ESP_LOGE(TAG, "Erro ao receber dados: errno=%d", errno);
            fclose(temp_file);
            mbedtls_sha256_free(&sha_ctx);
            return;
        }

        // Primeiro pacote DATA vem da porta efêmera do servidor
        if (first_packet)
        {
            server_tid_addr = data_addr;
            ESP_LOGI(TAG, "Servidor GSE usando TID (porta) %d", ntohs(server_tid_addr.sin_port));
            first_packet = 0;
        }

        if (ntohs(data_pkt.opcode) != OP_DATA)
        {
            ESP_LOGW(TAG, "Pacote inesperado recebido (opcode=%d)", ntohs(data_pkt.opcode));
            continue;
        }

        int data_len = n - 4;
        ESP_LOGI(TAG, "Bloco %d recebido (%d bytes)", ntohs(data_pkt.data.block), data_len);

        // Verifica se há espaço disponível na partição antes de escrever o bloco
        size_t total = 0, used = 0;
        esp_err_t ret = esp_spiffs_info("firmware", &total, &used);
        if (ret != ESP_OK)
        {
            ESP_LOGE(TAG, "Falha ao obter informações da partição: %s", esp_err_to_name(ret));
            fclose(temp_file);
            mbedtls_sha256_free(&sha_ctx);
            return;
        }

        size_t available = total - used;
        if (available < (size_t)data_len)
        {
            ESP_LOGE(TAG, "Espaço insuficiente na partição! Necessário=%d, Disponível=%u",
                     data_len, (unsigned)available);
            fclose(temp_file);
            mbedtls_sha256_free(&sha_ctx);
            return;
        }

        if (fwrite(data_pkt.data.data, 1, data_len, temp_file) != (size_t)data_len)
        {
            ESP_LOGE(TAG, "Failed to write to temp file: %s", TEMP_FILE_PATH);
            fclose(temp_file);
            mbedtls_sha256_free(&sha_ctx);
            return;
        }

        mbedtls_sha256_update(&sha_ctx, data_pkt.data.data, data_len);
        total_bytes += data_len;

        // Envia ACK para a porta efêmera do servidor
        tftp_packet_t ack;
        ack.opcode = htons(OP_ACK);
        ack.block = data_pkt.data.block;

        if (sendto(sock, &ack, 4, 0,
                   (struct sockaddr *)&server_tid_addr, sizeof(server_tid_addr)) < 0)
        {
            ESP_LOGE(TAG, "Erro ao enviar ACK: errno=%d", errno);
            fclose(temp_file);
            mbedtls_sha256_free(&sha_ctx);
            return;
        }

        if (data_len < BLOCK_SIZE)
            break;
    }

    if (total_bytes == 0)
    {
        ESP_LOGW(TAG, "Nenhum dado recebido em make_rrq para %s", filename);
        fclose(temp_file);
        mbedtls_sha256_free(&sha_ctx);
        return;
    }

    mbedtls_sha256_finish(&sha_ctx, hash);
    mbedtls_sha256_free(&sha_ctx);

    fclose(temp_file);

    ESP_LOGI(TAG, "Arquivo %s recebido como temp.bin (%u bytes). Hash calculado.", filename, (unsigned)total_bytes);
}