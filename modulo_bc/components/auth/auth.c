#include "auth.h"
#include "storage.h"
#include "tftp.h"

#include <string.h>
#include <stdio.h>
#include "esp_log.h"
#include "esp_timer.h"
#include "lwip/sockets.h"
#include <errno.h>

static const char *TAG = "auth";

// Flag para controlar se já foi autenticado
static bool authenticated = false;

// Chaves estáticas compatíveis com o script de teste GSE
static const uint8_t BC_STATIC_KEY[BC_KEY_SIZE] = "BC_SECRET_KEY_32_BYTES_EXACTLY!!";

static const uint8_t GSE_EXPECTED_KEY[GSE_KEY_SIZE] = "GSE_SECRET_KEY_32_BYTES_EXACTLY!";

esp_err_t auth_write_static_keys(void)
{
    ESP_LOGI(TAG, "Escrevendo chaves estáticas na partição");

    // Escreve chave do BC
    FILE *bc_file = fopen(BC_KEY_FILE, "wb");
    if (!bc_file)
    {
        ESP_LOGE(TAG, "Falha ao abrir arquivo da chave BC");
        return ESP_FAIL;
    }

    if (fwrite(BC_STATIC_KEY, 1, BC_KEY_SIZE, bc_file) != BC_KEY_SIZE)
    {
        ESP_LOGE(TAG, "Falha ao escrever chave BC");
        fclose(bc_file);
        return ESP_FAIL;
    }
    fclose(bc_file);

    // Escreve chave esperada do GSE
    FILE *gse_file = fopen(GSE_KEY_FILE, "wb");
    if (!gse_file)
    {
        ESP_LOGE(TAG, "Falha ao abrir arquivo da chave GSE");
        return ESP_FAIL;
    }

    if (fwrite(GSE_EXPECTED_KEY, 1, GSE_KEY_SIZE, gse_file) != GSE_KEY_SIZE)
    {
        ESP_LOGE(TAG, "Falha ao escrever chave GSE");
        fclose(gse_file);
        return ESP_FAIL;
    }
    fclose(gse_file);

    ESP_LOGI(TAG, "Chaves estáticas escritas com sucesso");
    return ESP_OK;
}

esp_err_t auth_load_keys(auth_keys_t *keys)
{
    if (!keys)
    {
        ESP_LOGE(TAG, "Ponteiro de chaves inválido");
        return ESP_ERR_INVALID_ARG;
    }

    ESP_LOGI(TAG, "Carregando chaves da partição");

    // Carrega chave do BC
    FILE *bc_file = fopen(BC_KEY_FILE, "rb");
    if (!bc_file)
    {
        ESP_LOGE(TAG, "Falha ao abrir arquivo da chave BC");
        return ESP_FAIL;
    }

    if (fread(keys->bc_auth_key, 1, BC_KEY_SIZE, bc_file) != BC_KEY_SIZE)
    {
        ESP_LOGE(TAG, "Falha ao ler chave BC");
        fclose(bc_file);
        return ESP_FAIL;
    }
    fclose(bc_file);

    // Carrega chave esperada do GSE
    FILE *gse_file = fopen(GSE_KEY_FILE, "rb");
    if (!gse_file)
    {
        ESP_LOGE(TAG, "Falha ao abrir arquivo da chave GSE");
        return ESP_FAIL;
    }

    if (fread(keys->gse_verify_key, 1, GSE_KEY_SIZE, gse_file) != GSE_KEY_SIZE)
    {
        ESP_LOGE(TAG, "Falha ao ler chave GSE");
        fclose(gse_file);
        return ESP_FAIL;
    }
    fclose(gse_file);

    ESP_LOGI(TAG, "Chaves carregadas com sucesso");
    return ESP_OK;
}

void auth_clear_keys(auth_keys_t *keys)
{
    if (keys)
    {
        ESP_LOGI(TAG, "Limpando buffers de chaves");
        memset(keys, 0, sizeof(auth_keys_t));
    }
}

esp_err_t auth_perform_handshake(int sock, struct sockaddr_in *client_addr, auth_keys_t *keys)
{
    // Verifica se já foi autenticado
    if (authenticated)
    {
        ESP_LOGI(TAG, "Sistema já autenticado, pulando handshake");
        return ESP_OK;
    }

    ESP_LOGI(TAG, "Iniciando handshake de autenticação");

    if (!keys)
    {
        ESP_LOGE(TAG, "Chaves não carregadas");
        return ESP_ERR_INVALID_ARG;
    }

    socklen_t addr_len = sizeof(*client_addr);
    tftp_packet_t packet;

    // Passo 1: Aguarda chave do GSE
    ESP_LOGI(TAG, "Aguardando chave do GSE...");

    int64_t start_time_us = esp_timer_get_time();
    int recv_len = -1;

    while (1)
    {
        addr_len = sizeof(*client_addr);
        recv_len = recvfrom(sock, &packet, sizeof(packet), 0,
                            (struct sockaddr *)client_addr, &addr_len);

        if (recv_len >= 0)
        {
            break; // Pacote recebido com sucesso
        }

        if (errno == EAGAIN || errno == EWOULDBLOCK)
        {
            int64_t elapsed_ms = (esp_timer_get_time() - start_time_us) / 1000;
            if (elapsed_ms >= 60000)
            {
                ESP_LOGW(TAG, "Timeout aguardando chave do GSE");
                return ESP_ERR_TIMEOUT;
            }

            // Mantém espera até que o GSE se conecte
            continue;
        }

        ESP_LOGE(TAG, "Erro ao receber chave do GSE: errno=%d", errno);
        return ESP_FAIL;
    }

    // Verifica se é um pacote DATA com a chave GSE
    if (ntohs(packet.opcode) != OP_DATA)
    {
        ESP_LOGE(TAG, "Pacote recebido não é DATA");
        return ESP_FAIL;
    }

    // Verifica se a chave recebida coincide com a esperada
    if (memcmp(packet.data.data, keys->gse_verify_key, GSE_KEY_SIZE) != 0)
    {
        ESP_LOGE(TAG, "Chave GSE inválida - autenticação falhou");
        return ESP_FAIL;
    }

    ESP_LOGI(TAG, "Chave GSE válida - enviando ACK");

    // Envia ACK para a chave recebida
    tftp_packet_t ack;
    ack.opcode = htons(OP_ACK);
    ack.block = packet.data.block;

    if (sendto(sock, &ack, 4, 0, (struct sockaddr *)client_addr, addr_len) < 0)
    {
        ESP_LOGE(TAG, "Erro ao enviar ACK");
        return ESP_FAIL;
    }

    // Passo 2: Envia chave do BC para GSE
    ESP_LOGI(TAG, "Enviando chave do BC...");

    tftp_packet_t bc_key_packet;
    bc_key_packet.opcode = htons(OP_DATA);
    bc_key_packet.data.block = htons(1);
    memcpy(bc_key_packet.data.data, keys->bc_auth_key, BC_KEY_SIZE);

    if (sendto(sock, &bc_key_packet, 4 + BC_KEY_SIZE, 0,
               (struct sockaddr *)client_addr, addr_len) < 0)
    {
        ESP_LOGE(TAG, "Erro ao enviar chave BC: errno=%d", errno);
        return ESP_FAIL;
    }

    // Aguarda ACK do GSE para nossa chave
    start_time_us = esp_timer_get_time();

    while (1)
    {
        addr_len = sizeof(*client_addr);
        recv_len = recvfrom(sock, &packet, sizeof(packet), 0,
                            (struct sockaddr *)client_addr, &addr_len);

        if (recv_len >= 0)
        {
            break;
        }

        if (errno == EAGAIN || errno == EWOULDBLOCK)
        {
            int64_t elapsed_ms = (esp_timer_get_time() - start_time_us) / 1000;
            if (elapsed_ms >= 60000)
            {
                ESP_LOGW(TAG, "Timeout aguardando ACK da chave BC");
                return ESP_ERR_TIMEOUT;
            }
            continue;
        }

        ESP_LOGE(TAG, "Erro ao receber ACK da chave BC: errno=%d", errno);
        return ESP_FAIL;
    }

    if (ntohs(packet.opcode) != OP_ACK)
    {
        ESP_LOGE(TAG, "GSE não confirmou chave BC");
        return ESP_FAIL;
    }

    ESP_LOGI(TAG, "Handshake de autenticação concluído com sucesso");
    authenticated = true; // Marca como autenticado
    return ESP_OK;
}

bool auth_is_authenticated(void)
{
    return authenticated;
}

void auth_reset_authentication(void)
{
    ESP_LOGI(TAG, "Resetando estado de autenticação");
    authenticated = false;
}