// Componentes criados
#include <wifi.h>
#include <storage.h>
#include <arinc.h>
#include <tftp.h>

// FreeRTOS & ESP-IDF
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"

// Network
#include <string.h> // memset, memcmp
#include <errno.h>
#include "lwip/sockets.h" // socket, bind, sendto, recvfrom, close
#include "lwip/inet.h"    // inet_ntoa

static const char *TAG = "B/C";
lur_data_t lur_file; // variável global, usado depois pelo Make_RRQ para saber o nome do arquivo (fw.bin)

void main_task(void *pvParameters)
{
    int sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0)
    {
        ESP_LOGE(TAG, "Erro ao criar socket: errno=%d", errno);
        vTaskDelete(NULL);
    }

    // CORREÇÃO: Timeout para recvfrom
    struct timeval tv;
    tv.tv_sec = TFTP_TIMEOUT_SEC;
    tv.tv_usec = 0;
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(TFTP_PORT);
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);

    if (bind(sock, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0)
    {
        ESP_LOGE(TAG, "Erro no bind: errno=%d", errno);
        close(sock);
        vTaskDelete(NULL);
    }

    ESP_LOGI(TAG, "Servidor TFTP rodando na porta %d", TFTP_PORT);

    while (1)
    {
        struct sockaddr_in client_addr;
        socklen_t addr_len = sizeof(client_addr);
        tftp_packet_t req;

        ssize_t n = recvfrom(sock, &req, sizeof(req), 0,
                             (struct sockaddr *)&client_addr, &addr_len);

        if (n < 0)
        {
            // CORREÇÃO: Timeout é esperado, não é erro crítico
            if (errno == EAGAIN || errno == EWOULDBLOCK)
            {
                // Timeout normal, continua loop
                continue;
            }
            ESP_LOGE(TAG, "Erro no recvfrom: errno=%d", errno);
            continue;
        }

        // CORREÇÃO: Validar tamanho mínimo do pacote
        if (n < 4)
        {
            ESP_LOGW(TAG, "Pacote muito pequeno recebido (%d bytes)", (int)n);
            continue;
        }

        uint16_t opcode = ntohs(req.opcode);
        if (opcode == OP_RRQ)
        {
            char *filename = req.request;
            // CORREÇÃO: Garantir terminação de string
            filename[n - 2] = '\0';
            handle_rrq(sock, &client_addr, filename);
        }
        else
        {
            ESP_LOGW(TAG, "Opcode desconhecido recebido: %d", opcode);
        }

        lus_data_t lus_data;
        if (init_lus(&lus_data, ARINC_STATUS_OP_ACCEPTED_NOT_STARTED,
                     "Operation Accepted", 0, "000") != 0)
        {
            ESP_LOGE(TAG, "Falha ao inicializar LUS inicial");
            continue;
        }

        make_wrq(sock, &client_addr, "INIT_LOAD.LUS", &lus_data);

        // Aguarda um write request do GSE para escrita do arquivo .LUR
        n = recvfrom(sock, &req, sizeof(req), 0,
                     (struct sockaddr *)&client_addr, &addr_len);
        if (n < 0)
        {
            ESP_LOGE(TAG, "Erro no recvfrom WRQ: errno=%d", errno);
            continue;
        }
        opcode = ntohs(req.opcode);
        if (opcode == OP_WRQ)
        {
            char *filename = req.request;
            // CORREÇÃO: Garantir terminação de string
            filename[n - 2] = '\0';
            handle_wrq(sock, &client_addr, filename, &lur_file);
        }
        else
        {
            ESP_LOGW(TAG, "Opcode desconhecido recebido: %d", opcode);
            continue;
        }
        // Faz um RRQ para obter o arquivo com o nome obtido do LUR
        unsigned char hash[32]; // SHA-256

        // CORREÇÃO: Salva o endereço original do cliente antes de make_rrq
        // porque make_rrq modifica client_addr para o TID efêmero do servidor
        struct sockaddr_in original_client_addr = client_addr;

        make_rrq(sock, &client_addr, lur_file.header_filename, hash);

        // Receber o hash com tftp e comparar com o calculado
        // Hash vem do TID efêmero que make_rrq detectou
        if (recvfrom(sock, &req, sizeof(req), 0,
                     (struct sockaddr *)&client_addr, &addr_len) < 0)
        {
            ESP_LOGE(TAG, "Erro no recvfrom do hash: errno=%d", errno);
            continue;
        }

        // Envia ACK para o hash recebido
        tftp_packet_t hash_ack;
        hash_ack.opcode = htons(OP_ACK);
        hash_ack.block = req.data.block; // Mantém o mesmo número do bloco recebido
        if (sendto(sock, &hash_ack, 4, 0,
                   (struct sockaddr *)&client_addr, addr_len) < 0)
        {
            ESP_LOGE(TAG, "Erro ao enviar ACK do hash: errno=%d", errno);
            continue;
        }
        ESP_LOGI(TAG, "ACK enviado para hash (bloco %d)", ntohs(req.data.block));

        // CORREÇÃO: Restaura endereço original do cliente para envio de LUS
        // LUS deve ser enviado para o socket principal do GSE, não para o TID efêmero
        client_addr = original_client_addr;
        ESP_LOGI(TAG, "Endereço do cliente restaurado para IP=%s, porta=%d",
                 inet_ntoa(client_addr.sin_addr), ntohs(client_addr.sin_port));

        if (memcmp(req.data.data, hash, 32) != 0)
        {
            ESP_LOGE(TAG, "Hash SHA-256 não confere! Arquivo corrompido.");
        }
        else
        {
            ESP_LOGI(TAG, "Hash SHA-256 conferido com sucesso.");
            // Envio do LUS intermediário
            lus_data_t intermediate_lus_data;
            if (init_lus(&intermediate_lus_data, ARINC_STATUS_OP_IN_PROGRESS,
                         "Intermediate Load Accepted", 1, "050") != 0)
            {
                ESP_LOGE(TAG, "Falha ao inicializar LUS intermediário");
                continue;
            }

            make_wrq(sock, &client_addr, "INTERMEDIATE_LOAD.LUS", &intermediate_lus_data);

            // armazena arquivo na partição SPIFFS: move/copia de /temp para /storage
            if (move_temp_to_storage(lur_file.header_filename) != ESP_OK)
            {
                ESP_LOGE(TAG, "Falha ao mover arquivo para storage");
                continue;
            }

            // Envio do LUS final
            lus_data_t final_lus_data;
            if (init_lus(&final_lus_data, ARINC_STATUS_OP_COMPLETED_OK,
                         "Load Completed Successfully", 2, "100") != 0)
            {
                ESP_LOGE(TAG, "Falha ao inicializar LUS final");
                continue;
            }
            make_wrq(sock, &client_addr, "FINAL_LOAD.LUS", &final_lus_data);
        }
    }

    close(sock);
    vTaskDelete(NULL);
}

void app_main(void)
{
    ESP_LOGI(TAG, "Iniciando ESP32");

    nvs_flash_init();
    wifi_init_softap();

    mount_spiffs("temp", TEMP_MOUNT_POINT);
    mount_spiffs("storage", STORAGE_MOUNT_POINT);

    xTaskCreate(main_task, "main", 16384, NULL, 5, NULL);
}