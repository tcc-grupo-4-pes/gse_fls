#include "tftp.h"
#include "storage.h"           // open_temp_file, FIRMWARE_MOUNT_POINT
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
#include <stdbool.h>

#define MIN_AVAILABLE_SPACE 500000 // Para evitar Page Fault
static const char *TAG = "tftp";

void handle_rrq(int sock, struct sockaddr_in *client, char *filename)
{
    ESP_LOGI(TAG, "Read Request(GSE requisita): %s", filename);

    /* BC-LLR-21 Erro no Read Request da inicialização de upload(LUI)
    No estado MAINT_WAIT após autenticação do GSE como aplicação Embraer,
    caso a requisição não for de leitura de um arquivo .LUI,
     o software deve desconsiderar e esperar novo pacote*/
    if (strstr(filename, ".LUI") == NULL)
    {
        ESP_LOGW(TAG, "Arquivo requisitado não e .LUI");
        return;
    }

    /* BC-LLR-23 */
    int transfer_sock = socket(AF_INET, SOCK_DGRAM, 0);
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
    socklen_t addr_len = sizeof(transfer_addr);
    getsockname(transfer_sock, (struct sockaddr *)&transfer_addr, &addr_len);
    ESP_LOGI(TAG, "Socket de transferência criado na porta %d (TID)", ntohs(transfer_addr.sin_port)); /*BC-LLR-89*/

    /* BC-LLR-24 Criação do arquivo .LUI
    No estado MAINT_WAIT, após receber a requisição de leitura do arquivo de inicialização deve criar
    e enviar por um buffer o Load Upload Initialization(LUI) aceitando a operação caso não haja nenhum
    problema    */
    lui_data_t lui;
    if (init_lui(&lui, ARINC_STATUS_OP_ACCEPTED_NOT_STARTED, "Operation Accepted") != 0)
    {
        /*BC-LLR-52 Erro ao criar o .LUI
        No estado MAINT_WAIT, caso haja algum erro ao criar o arquivo .LUI,
        o software deve ir para o estado de ERROR e parar a execução
        */
        ESP_LOGE(TAG, "Falha ao inicializar LUI");
        close(transfer_sock);
        return;
    }

    /* BC-LLR-24 */
    size_t lui_size = sizeof(lui_data_t);

    tftp_packet_t pkt;
    /* BC-LLR-90 Conversão do OPCODE - Envio
    Ao enviar um pacote via TFTP, o software do B/C deve converter o OPCODE do formato
    host (little-endian do ESP32) para o de rede (big-endian)
    */
    pkt.opcode = htons(OP_DATA);
    pkt.data.block = htons(1);
    memcpy(pkt.data.data, &lui, lui_size);

    /* BC-LLR-23 */
    if (sendto(transfer_sock, &pkt, 4 + lui_size, 0,
               (struct sockaddr *)client, sizeof(*client)) < 0)
    {
        /* BC-LLR-53 Erro ao enviar o .LUI
        No estado MAINT_WAIT, caso haja algum erro ao enviar o arquivo .LUI para responder a
        requisição de leitura, o software deve ir para o estado de ERROR e parar a execução */
        ESP_LOGE(TAG, "Erro ao enviar LUI: errno=%d", errno);
        close(transfer_sock);
        return;
    }
    ESP_LOGI(TAG, "LUI enviado: bloco 1 (%u bytes)", (unsigned)lui_size);

    /*BC-LLR-27 Espera do ACK no TFTP
    Conforme TFTP, o software do B/C deve esperar um ACK de cada pacote
    enviado antes de enviar um novo pacote*/
    struct timeval tv;
    tv.tv_sec = TFTP_TIMEOUT_SEC; /* BC-LLR-16 */
    tv.tv_usec = 0;
    setsockopt(transfer_sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

    tftp_packet_t ack;
    struct sockaddr_in ack_addr;
    ssize_t n = -1;
    int retries = 0;

    while (1)
    {
        socklen_t ack_len = sizeof(ack_addr);
        /*BC-LLR-27*/
        n = recvfrom(transfer_sock, &ack, sizeof(ack), 0,
                     (struct sockaddr *)&ack_addr, &ack_len);

        if (n >= 0)
        {
            break;
        }
        /* BC-LLR-29 Retransmissão de pacotes TFTP
        Em caso de ACK não recebido ao enviar um pacote, 
        o software do B/C deve retransmitir o pacote somente 1 vez */
        if ((errno == EAGAIN || errno == EWOULDBLOCK) && retries < TFTP_RETRY_LIMIT)
        {
            retries++;
            ESP_LOGW(TAG, "Timeout aguardando ACK do bloco 1, reenviando LUI (%d/%d)",
                     retries, TFTP_RETRY_LIMIT);
            if (sendto(transfer_sock, &pkt, 4 + lui_size, 0,
                       (struct sockaddr *)client, sizeof(*client)) < 0)
            {
                ESP_LOGE(TAG, "Erro ao reenviar LUI: errno=%d", errno);
                close(transfer_sock);
                return;
            }
            continue;
        }

        ESP_LOGE(TAG, "Erro ao receber ACK do bloco 1: errno=%d", errno);
        close(transfer_sock);
        return;
    }

    /* BC-LLR-89 , BC-LLR-53*/
    if (ntohs(ack.opcode) != OP_ACK || ntohs(ack.block) != 1)
    {
        ESP_LOGE(TAG, "ACK não recebido ou inválido para bloco 1");
        close(transfer_sock);
        return;
    }

    ESP_LOGI(TAG, "ACK recebido para bloco 1 - LUI enviado com sucesso");

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

    /* BC-LLR 23 Porta Efêmera para transferência */
    int transfer_sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (transfer_sock < 0)
    {
        ESP_LOGE(TAG, "Erro ao criar socket de transferência: errno=%d", errno);
        return;
    }

    /* BC-LLR-23*/
    struct sockaddr_in transfer_addr;
    memset(&transfer_addr, 0, sizeof(transfer_addr));
    transfer_addr.sin_family = AF_INET;
    transfer_addr.sin_port = htons(0); // Porta efêmera
    transfer_addr.sin_addr.s_addr = htonl(INADDR_ANY);

    if (bind(transfer_sock, (struct sockaddr *)&transfer_addr, sizeof(transfer_addr)) < 0)
    {
        /* BC-LLR-51 Erro no bind do socket de transferência */
        ESP_LOGE(TAG, "Erro no bind do socket de transferência: errno=%d", errno);
        close(transfer_sock);
        return;
    }

    /* BC-LLR-23 */
    socklen_t addr_len = sizeof(transfer_addr);
    getsockname(transfer_sock, (struct sockaddr *)&transfer_addr, &addr_len);
    ESP_LOGI(TAG, "Socket de transferência criado na porta %d (TID)", ntohs(transfer_addr.sin_port)); /*BC-LLR-89*/

    // Envia ACK(0) do socket efêmero para o cliente
    tftp_packet_t ack;
    ack.opcode = htons(OP_ACK); /*BC-LLR-90*/
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
                             (struct sockaddr *)&recv_addr, &recv_len); /*BC-LLR-27*/
        if (n < 0)
        {
            ESP_LOGW(TAG, "Timeout ou erro no recebimento (errno=%d)", errno);
            break;
        }

        if (ntohs(pkt.opcode) != OP_DATA || ntohs(pkt.data.block) != expected_block) /*BC-LLR-89*/
        {
            /* BC-LLR-18*/
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

        ack.opcode = htons(OP_ACK); /*BC-LLR-90*/
        ack.block = htons(expected_block);
        sendto(transfer_sock, &ack, 4, 0, (struct sockaddr *)client, sizeof(*client)); /*BC-LLR-28*/

        ESP_LOGI(TAG, "Bloco %d recebido (%d bytes)", expected_block, data_len);
        expected_block++;

        if (data_len < BLOCK_SIZE)
            break; // Último bloco
    }

    if (total_received == 0)
    {
        ESP_LOGW(TAG, "Nenhum dado .LUR recebido");
        close(transfer_sock);
        return;
    }

    if (parse_lur(lur_buf, total_received, lur_file) != 0)
    {
        /* BC-LLR-57 Erro no parse do arquivo .LUR
        No estado UPLOAD_PREP, após armazenar em um buffer o arquivo .LUR,
        caso haja algum erro ao parsear o arquivo para obter as informações de PN e nome do arquivo,
         o software deve ir para o estado ERROR e parar a execução
        */
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

/* BC-LLR-30 */
void make_wrq(int sock, struct sockaddr_in *client_addr, const char *lus_filename, const lus_data_t *lus_data)
{
    ESP_LOGI(TAG, "Iniciando WRQ para envio de %s", lus_filename);

    tftp_packet_t wrq;
    wrq.opcode = htons(OP_WRQ); /*BC-LLR-90*/
    snprintf(wrq.request, sizeof(wrq.request), "%s%coctet%c", lus_filename, 0, 0);

    if (sendto(sock, &wrq, strlen(lus_filename) + 8, 0,
               (struct sockaddr *)client_addr, sizeof(*client_addr)) < 0)
    {
        /*BC-LLR-69 - Erro ao enviar o FINAL.LUS
        No estado TEARDOWN, caso haja algum erro ao fazer a requisição de escrita e envio do arquivo FINAL.LUS,
        o software deve escrever log de erro e cancelar o envio*/
        ESP_LOGE(TAG, "Erro ao enviar WRQ: errno=%d", errno);
        return;
    }

    /* BC-LLR-23 */
    // Aguarda ACK(0) que virá da porta efêmera do cliente
    tftp_packet_t ack;
    struct sockaddr_in ack_addr;
    socklen_t ack_len = sizeof(ack_addr);
    ssize_t n = -1;
    int retries = 0;

    size_t wrq_len = strlen(lus_filename) + 8;

    while (1)
    {
        ack_len = sizeof(ack_addr);
        if ((n = recvfrom(sock, &ack, sizeof(ack), 0,
                          (struct sockaddr *)&ack_addr, &ack_len)) >= 0)
        {
            break;
        }
        /* BC-LLR-29 */
        if ((errno == EAGAIN || errno == EWOULDBLOCK) && retries < TFTP_RETRY_LIMIT)
        {
            retries++;
            ESP_LOGW(TAG, "Timeout aguardando ACK inicial, reenviando WRQ (%d/%d)",
                     retries, TFTP_RETRY_LIMIT);
            if (sendto(sock, &wrq, wrq_len, 0,
                       (struct sockaddr *)client_addr, sizeof(*client_addr)) < 0)
            {
                ESP_LOGE(TAG, "Erro ao reenviar WRQ: errno=%d", errno);
                return;
            }
            continue;
        }

        ESP_LOGE(TAG, "Erro ao receber ACK inicial: errno=%d", errno);
        return;
    }

    if (ntohs(ack.opcode) != OP_ACK || ntohs(ack.block) != 0) /*BC-LLR-89*/
    {
        ESP_LOGE(TAG, "ACK inicial invalido");
        return;
    }

    /* BC-LLR-23 */
    // Cliente mudou para porta efêmera, salva o novo endereço
    ESP_LOGI(TAG, "Cliente mudou para TID (porta) %d", ntohs(ack_addr.sin_port));

    // BBC-LLR-16
    tftp_packet_t data_pkt;
    data_pkt.opcode = htons(OP_DATA); /*BC-LLR-90*/
    data_pkt.data.block = htons(1);
    memcpy(data_pkt.data.data, lus_data, sizeof(lus_data_t));

    /*  BC-LLR-51 Erro no socket - UPLOAD_PREP
    No estado UPLOAD_PREP, caso haja algum erro ao criar ou dar o bind no socket de transferência
    (criado com porta efêmera), o software deve ir para o estado de ERROR e parar a execução*/
    if (sendto(sock, &data_pkt, 4 + sizeof(lus_data_t), 0,
               (struct sockaddr *)&ack_addr, sizeof(ack_addr)) < 0)
    {
        ESP_LOGE(TAG, "Erro ao enviar dados LUS: errno=%d", errno);
        return;
    }

    retries = 0;
    while (1)
    {
        ack_len = sizeof(ack_addr);
        if ((n = recvfrom(sock, &ack, sizeof(ack), 0,
                          (struct sockaddr *)&ack_addr, &ack_len)) >= 0) /*BC-LLR-27*/
        {
            break;
        }

        if ((errno == EAGAIN || errno == EWOULDBLOCK) && retries < TFTP_RETRY_LIMIT)
        {
            retries++;
            ESP_LOGW(TAG, "Timeout aguardando ACK final, reenviando bloco 1 (%d/%d)",
                     retries, TFTP_RETRY_LIMIT);
            if (sendto(sock, &data_pkt, 4 + sizeof(lus_data_t), 0,
                       (struct sockaddr *)&ack_addr, sizeof(ack_addr)) < 0)
            {
                ESP_LOGE(TAG, "Erro ao reenviar dados LUS: errno=%d", errno);
                return;
            }
            continue;
        }

        ESP_LOGE(TAG, "Erro ao receber ACK final: errno=%d", errno);
        return;
    }

    if (ntohs(ack.opcode) != OP_ACK || ntohs(ack.block) != 1) /*BC-LLR-89*/
    {
        ESP_LOGE(TAG, "ACK final invalido");
        return;
    }

    ESP_LOGI(TAG, "Arquivo LUS enviado com sucesso");
}

void make_rrq(int sock, struct sockaddr_in *client_addr, const char *filename, unsigned char *hash)
{
    ESP_LOGI(TAG, "Iniciando RRQ para %s", filename);

    /* BC-LLR-36 Armazenamento dos pacotes recebidos
       No estado UPLOADING, ao receber os pacotes do firmware,
       o software deve salvar os dados em um caminho temporário dentro da partição firmware
    */
    FILE *temp_file = open_temp_file();

    /* BC-LLR-59 Erro ao abrir partição
       No estado UPLOADING, caso haja algum erro ao abrir a partição para escrita dos dados
       recebidos de maneira temporária, o software deve ir para o estado de ERROR e parar a execução da tarefa
    */
    if (!temp_file)
    {
        ESP_LOGE(TAG, "Failed to open temporary file for write");
        return;
    }

    /* BC-LLR-94 Envio de Read Request (RRQ)
       No estado UPLOADING, o software deve enviar uma requisição TFTP RRQ para o GSE
       solicitando o arquivo de firmware especificado no LUR
    */
    tftp_packet_t rrq;
    rrq.opcode = htons(OP_RRQ); /*BC-LLR-90*/
    snprintf(rrq.request, sizeof(rrq.request), "%s%coctet%c", filename, 0, 0);

    if (sendto(sock, &rrq, strlen(filename) + 8, 0,
               (struct sockaddr *)client_addr, sizeof(*client_addr)) < 0)
    {
        /* BC-LLR-95 Erro no envio do RRQ
        No estado UPLOADING, caso haja erro ao enviar o RRQ,
        o software deve fechar o arquivo temporário e parar a execução
        */
        ESP_LOGE(TAG, "Erro ao enviar RRQ: errno=%d", errno);
        fclose(temp_file);
        return;
    }

    /* BC-LLR-37 Cálculo contínuo do SHA256
       No estado UPLOADING, ao receber os pacotes do firmware,
       o software deve inicializar o cálculo do SHA256 usando mbedtls e
       atualizar o cálculo do SHA256 continuamente
    */
    mbedtls_sha256_context sha_ctx;
    mbedtls_sha256_init(&sha_ctx);
    mbedtls_sha256_starts(&sha_ctx, 0);

    size_t total_bytes = 0;
    struct sockaddr_in server_tid_addr; // Porta efêmera do servidor (GSE) BC-LLR-23
    int first_packet = 1;
    bool pn_checked = false; // Verificação de PN feita no primeiro pacote

    while (1)
    {
        tftp_packet_t data_pkt;
        struct sockaddr_in data_addr;
        socklen_t addr_len = sizeof(data_addr);

        ssize_t n = recvfrom(sock, &data_pkt, sizeof(data_pkt), 0,
                             (struct sockaddr *)&data_addr, &addr_len);

        /* BC-LLR-96 Erro ao receber pacote de dados do firmware
           No estado UPLOADING, caso haja erro ao receber um pacote de dados via TFTP,
           o software deve fechar o arquivo temporário, parar o cálculo do SHA256,
           e ir para o estado ERROR
        */
        if (n < 0)
        {
            ESP_LOGE(TAG, "Erro ao receber dados: errno=%d", errno);
            fclose(temp_file);
            mbedtls_sha256_free(&sha_ctx);
            return;
        }

        /* BC-LLR-97 Detecção do TID efêmero
           No estado UPLOADING, ao receber o primeiro pacote DATA, o software deve identificar
           e salvar o TID (porta efêmera) do servidor GSE para envio dos ACKs subsequentes
        */
        if (first_packet)
        {
            server_tid_addr = data_addr;
            ESP_LOGI(TAG, "Servidor GSE usando TID (porta) %d", ntohs(server_tid_addr.sin_port)); /*BC-LLR-89*/
            first_packet = 0;
        }

        /* BC-LLR-61 Erro: Não é pacote de dados durante recebimento do firmware
           No estado UPLOADING, ao receber os pacotes do firmware,
           caso seja recebido um pacote TFTP que não tenha OP code de DATA,
           o software deve desconsiderar o pacote e esperar um novo pacote
        */
        if (ntohs(data_pkt.opcode) != OP_DATA) /*BC-LLR-89*/
        {
            /*BC-LLR-18*/
            ESP_LOGW(TAG, "Pacote inesperado recebido (opcode=%d)", ntohs(data_pkt.opcode));
            continue;
        }

        int data_len = n - 4;
        ESP_LOGI(TAG, "Bloco %d recebido (%d bytes)", ntohs(data_pkt.data.block), data_len);

        /* BC-LLR-103 Compatibilidade do PN de hardware
        No primeiro pacote de dados do firmware, o software deve verificar se o PN de Hardware
        (ler 20 bytes depois do byte 20 do pacote conforme BC-ARTG-11) é compatível com o PN
        do Hardware do módulo
        */
        if (!pn_checked && total_bytes == 0)
        {
            const size_t PN_OFFSET = 20; /* BC-ARTG-11 */
            const size_t PN_SIZE = 20;   /* BC-ARTG-11 */
            if (data_len >= (int)(PN_OFFSET + PN_SIZE))
            {
                const unsigned char *pn_ptr = (const unsigned char *)data_pkt.data.data + PN_OFFSET;

                /* BC-LLR-103 */
                if (memcmp(pn_ptr, HW_PN, PN_SIZE) != 0)
                {
                    /* BC-LLR-104 Erro de compatibilidade do PN de hardware
                    Ao verificar a compatibilidade do PN-HW no primeiro pacote do firmware, caso o PN de hardware
                    extraído não seja igual ao do módulo B/C, o software deve fechar a escrita do arquivo temporário,
                    parar o cálculo incremental do SHA256 e retornar indicando falha*/
                    ESP_LOGE(TAG, "PN inválido no firmware recebido. Abortando recebimento.");
                    fclose(temp_file);
                    mbedtls_sha256_free(&sha_ctx);
                    upload_failure_count++;
                    return;
                }
                ESP_LOGI(TAG, "PN de hardware verificado com sucesso no primeiro pacote: %s", HW_PN);
                pn_checked = true; /* Apenas entra nessa condição no primeiro pacote*/
            }
            else
            {
                ESP_LOGW(TAG, "Primeiro pacote menor que %u bytes; PN não pôde ser verificado ainda", (unsigned)(PN_OFFSET + PN_SIZE));
            }
        }

        /* BC-LLR-38 Verificação de tamanho
           No estado UPLOADING, no loop de recebimento dos pacotes do firmware,
           o software do B/C deve fazer uma verificação se há espaço na partição firmware
           para escrita do pacote
        */
        size_t total = 0, used = 0;
        esp_err_t ret = esp_spiffs_info("firmware", &total, &used);

        /* BC-LLR-98 Erro ao obter informações da partição
           No estado UPLOADING, caso haja erro ao obter informações de espaço da partição,
           o software deve fechar o arquivo temporário, parar o cálculo do SHA256,
           e ir para o estado ST_ERROR
        */
        if (ret != ESP_OK)
        {
            ESP_LOGE(TAG, "Falha ao obter informações da partição: %s", esp_err_to_name(ret));
            fclose(temp_file);
            mbedtls_sha256_free(&sha_ctx);
            return;
        }

        size_t available = total - used;

        /* BC-LLR-60 Erro de espaço insuficiente
           No estado UPLOADING, caso não haja espaço na partição para escrita do pacote
           recebido de firmware, o software deve fechar o arquivo temporário,
           parar o cálculo contínuo do SHA256, ir para estado ERROR e parar execução da tarefa
        */
        if (available < MIN_AVAILABLE_SPACE)
        {
            ESP_LOGE(TAG, "Espaço insuficiente na partição!");
            fclose(temp_file);
            mbedtls_sha256_free(&sha_ctx);
            return;
        }

        /* BC-LLR-36 Armazenamento dos pacotes recebidos
           Escreve os dados recebidos no arquivo temporário
        */

        if (fwrite(data_pkt.data.data, 1, data_len, temp_file) != (size_t)data_len)
        {
            /* BC-LLR-99 Erro na escrita do arquivo temporário
            No estado UPLOADING, caso haja erro ao escrever dados no arquivo temporário,
            o software deve fechar o arquivo, parar o cálculo do SHA256, e ir para o estado ERROR
            */
            ESP_LOGE(TAG, "Failed to write to temp file: %s", TEMP_FILE_PATH);
            fclose(temp_file);
            mbedtls_sha256_free(&sha_ctx);
            return;
        }

        /* BC-LLR-37 Cálculo contínuo do SHA256
        No estado UPLOADING, ao receber os pacotes do firmware,
        o software deve inicializar o cálculo do SHA256 usando mbedtls
        e atualizar o cálculo do SHA256 continuamente
        */
        mbedtls_sha256_update(&sha_ctx, data_pkt.data.data, data_len);
        total_bytes += data_len;

        // Envia ACK para a porta efêmera do servidor
        tftp_packet_t ack;
        ack.opcode = htons(OP_ACK);
        ack.block = data_pkt.data.block;

        /* BC-LLR-62 Erro no envio do ACK
           No estado UPLOADING, caso haja erro ao enviar o ACK referente ao pacote de firmware recebido,
           o software deve fechar o arquivo temporário, parar o cálculo contínuo do SHA256,
           ir para o estado ERROR e parar a execução
        */
        if (sendto(sock, &ack, 4, 0,
                   (struct sockaddr *)&server_tid_addr, sizeof(server_tid_addr)) < 0) /*BC-LLR-28, BC-LLR-23*/
        {
            ESP_LOGE(TAG, "Erro ao enviar ACK: errno=%d", errno);
            fclose(temp_file);
            mbedtls_sha256_free(&sha_ctx);
            return;
        }

        /* BC-LLR-39 Último pacote de dados do firmware
           No estado UPLOADING, o software irá parar de receber os pacotes do firmware
           quando for detectado um pacote de dados menor que 512 bytes
        */
        if (data_len < BLOCK_SIZE)
            break;
    }

    /* BC-LLR-100 Validação de recebimento de firmware nulo
       No estado UPLOADING, caso nenhum byte de firmware seja recebido,
       o software deve fechar o arquivo temporário, parar o cálculo do SHA256, e retornar erro
    */
    if (total_bytes == 0)
    {
        ESP_LOGW(TAG, "Nenhum dado recebido em make_rrq para %s", filename);
        fclose(temp_file);
        mbedtls_sha256_free(&sha_ctx);
        return;
    }

    /* BC-LLR-37 Cálculo contínuo do SHA256
       No estado UPLOADING, ao receber os pacotes do firmware,
       o software deve inicializar o cálculo do SHA256 usando mbedtls
       e atualizar o cálculo do SHA256 continuamente
    */
    mbedtls_sha256_finish(&sha_ctx, hash);
    mbedtls_sha256_free(&sha_ctx);

    fclose(temp_file);

    ESP_LOGI(TAG, "Arquivo %s recebido como temp.bin (%u bytes). Hash calculado.", filename, (unsigned)total_bytes);
}