#include "tftp.h"
#include "storage.h" // open_temp_file, TEMP_MOUNT_POINT

#include <stdio.h>  // FILE operations
#include <string.h> // strstr, memcpy
#include <errno.h>  // errno
#include <stdlib.h> // malloc, free

#include "esp_log.h"
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

    lui_data_t lui;
    if (init_lui(&lui, ARINC_STATUS_OP_ACCEPTED_NOT_STARTED, "Operation Accepted") != 0)
    {
        ESP_LOGE(TAG, "Falha ao inicializar LUI");
        return;
    }

    size_t total_size = sizeof(lui_data_t);
    uint8_t *lui_buf = malloc(total_size);
    if (lui_buf == NULL)
    {
        ESP_LOGE(TAG, "Falha ao alocar memoria para LUI");
        return;
    }

    memcpy(lui_buf, &lui, total_size);

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

        ssize_t s = sendto(sock, &pkt, 4 + chunk, 0,
                           (struct sockaddr *)client, sizeof(*client));
        if (s < 0)
        {
            ESP_LOGW(TAG, "Falha ao enviar bloco %d, tentando novamente", block);
            retry_count++;
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
        setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

        tftp_packet_t ack;
        struct sockaddr_in ack_addr;
        socklen_t ack_len = sizeof(ack_addr);

        ssize_t n = recvfrom(sock, &ack, sizeof(ack), 0,
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

    free(lui_buf);
    ESP_LOGI(TAG, "RRQ concluido");
}

void handle_wrq(int sock, struct sockaddr_in *client, char *filename, lur_data_t *lur_file)
{
    ESP_LOGI(TAG, "Write Request (GSE envia): %s", filename);

    if (strstr(filename, ".LUR") == NULL)
    {
        ESP_LOGW(TAG, "Arquivo recebido nao e .LUR");
        return;
    }

    tftp_packet_t ack;
    ack.opcode = htons(OP_ACK);
    ack.block = htons(0);
    sendto(sock, &ack, 4, 0, (struct sockaddr *)client, sizeof(*client));

    struct timeval tv;
    tv.tv_sec = TFTP_TIMEOUT_SEC;
    tv.tv_usec = 0;
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

    uint16_t expected_block = 1;
    tftp_packet_t pkt;
    struct sockaddr_in recv_addr;
    socklen_t recv_len = sizeof(recv_addr);

    uint8_t lur_buf[256];
    size_t total_received = 0;

    while (1)
    {
        ssize_t n = recvfrom(sock, &pkt, sizeof(pkt), 0,
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
        sendto(sock, &ack, 4, 0, (struct sockaddr *)client, sizeof(*client));

        ESP_LOGI(TAG, "Bloco %d recebido (%d bytes)", expected_block, data_len);
        expected_block++;

        if (data_len < BLOCK_SIZE)
            break; // Ultimo bloco
    }

    if (total_received == 0)
    {
        ESP_LOGW(TAG, "Nenhum dado .LUR recebido");
        return;
    }

    // parse LUR using arinc helper
    if (parse_lur(lur_buf, total_received, lur_file) != 0)
    {
        ESP_LOGE(TAG, "Falha ao parsear LUR");
        return;
    }

    ESP_LOGI(TAG, "LUR recebido e processado da RAM:");
    ESP_LOGI(TAG, "  File length: %lu", ntohl(lur_file->file_length));
    ESP_LOGI(TAG, "  Protocol version: %s", lur_file->protocol_version);
    ESP_LOGI(TAG, "  Header file name: %s", lur_file->header_filename);
    ESP_LOGI(TAG, "  Load Part Number: %s", lur_file->load_part_number);
}

void make_wrq(int sock, struct sockaddr_in *client_addr, const char *lus_filename, const lus_data_t *lus_data)
{
    ESP_LOGI(TAG, "Iniciando WRQ para envio de %s", lus_filename);

    tftp_packet_t wrq;
    wrq.opcode = htons(OP_WRQ);
    snprintf(wrq.request, sizeof(wrq.request), "%s%coctet%c", lus_filename, 0, 0);

    if (sendto(sock, &wrq, strlen(lus_filename) + 8, 0,
               (struct sockaddr *)client_addr, sizeof(*client_addr)) < 0)
    {
        ESP_LOGE(TAG, "Erro ao enviar WRQ: errno=%d", errno);
        return;
    }

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

    tftp_packet_t data_pkt;
    data_pkt.opcode = htons(OP_DATA);
    data_pkt.data.block = htons(1);
    memcpy(data_pkt.data.data, lus_data, sizeof(lus_data_t));

    if (sendto(sock, &data_pkt, 4 + sizeof(lus_data_t), 0,
               (struct sockaddr *)client_addr, sizeof(*client_addr)) < 0)
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
    char temp_path[512];
    snprintf(temp_path, sizeof(temp_path), "%s/%s", TEMP_MOUNT_POINT, filename);

    FILE *temp_file = fopen(temp_path, "wb");
    if (!temp_file)
    {
        ESP_LOGE(TAG, "Failed to open temporary file for write: %s", temp_path);
        return;
    }

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

        if (ntohs(data_pkt.opcode) != OP_DATA)
        {
            ESP_LOGW(TAG, "Pacote inesperado recebido (opcode=%d)", ntohs(data_pkt.opcode));
            continue;
        }

        int data_len = n - 4;
        ESP_LOGI(TAG, "Bloco %d recebido (%d bytes)", ntohs(data_pkt.data.block), data_len);

        if (fwrite(data_pkt.data.data, 1, data_len, temp_file) != (size_t)data_len)
        {
            ESP_LOGE(TAG, "Failed to write to temp file: %s", temp_path);
            fclose(temp_file);
            mbedtls_sha256_free(&sha_ctx);
            return;
        }

        mbedtls_sha256_update(&sha_ctx, data_pkt.data.data, data_len);
        total_bytes += data_len;

        tftp_packet_t ack;
        ack.opcode = htons(OP_ACK);
        ack.block = data_pkt.data.block;

        if (sendto(sock, &ack, 4, 0,
                   (struct sockaddr *)client_addr, sizeof(*client_addr)) < 0)
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

    ESP_LOGI(TAG, "Arquivo %s recebido em %s (%u bytes). Hash calculado.", filename, TEMP_MOUNT_POINT, (unsigned)total_bytes);
}
