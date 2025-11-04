#include "auth.h"
#include "storage.h"
#include "tftp.h"

#include <string.h>
#include <stdio.h>
#include "esp_log.h"
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
    /* BC-LLR-80 - Validação de Ponteiro de Estrutura de Chaves
    No modo MAINT_WAIT, antes de carregar as chaves de autenticação da partição SPIFFS,
    o sistema deve validar se o ponteiro para a estrutura de destino é válido (não nulo). 
    Em caso de ponteiro inválido, o sistema deve registrar erro crítico 
    e retornar código de erro ESP_ERR_INVALID_ARG  0x102, 
    evitando acesso inválido à memória e falha de segmentação.
    */
    if (!keys)
    {
        ESP_LOGE(TAG, "Ponteiro de chaves inválido");
        return ESP_ERR_INVALID_ARG;
    }

    ESP_LOGI(TAG, "Carregando chaves da partição");

    FILE *bc_file = fopen(BC_KEY_FILE, "rb");
    /* BC-LLR-81 - Validação de Abertura de Arquivo de Chave BC
    No modo MAINT_WAIT, caso ocorra erro ao abrir o arquivo /keys/bc_key.bin
    em modo leitura binária, o B/C deve registrar erro e retornar o erro 
    ESP_FAIL -1
    */
    if (!bc_file)
    {
        ESP_LOGE(TAG, "Falha ao abrir arquivo da chave BC");
        return ESP_FAIL;
    }

    /* BC-LLR-82 - Validação de Leitura de Chave BC
    No modo MAINT_WAIT, após abrir o arquivo /keys/bc_key.bin, o B/C deve
    ler exatamente 32 bytes para o buffer de chave BC. Caso a leitura 
    retorne quantidade diferente de 32 bytes, o B/C deve registrar erro,
    fechar o arquivo e retornar o erro ESP_FAIL -1
    */
    if (fread(keys->bc_auth_key, 1, BC_KEY_SIZE, bc_file) != BC_KEY_SIZE)
    {
        ESP_LOGE(TAG, "Falha ao ler chave BC");
        fclose(bc_file);
        return ESP_FAIL;
    }
    fclose(bc_file);

    /* BC-LLR-83 - Validação de Abertura de Arquivo de Chave GSE
    No modo MAINT_WAIT, caso ocorra erro ao abrir o arquivo /keys/gse_key.bin
    em modo leitura binária, o B/C deve registrar erro e retornar o erro 
    ESP_FAIL -1
    */
    FILE *gse_file = fopen(GSE_KEY_FILE, "rb");
    if (!gse_file)
    {
        ESP_LOGE(TAG, "Falha ao abrir arquivo da chave GSE");
        return ESP_FAIL;
    }

    /* BC-LLR-84 - Validação de Leitura de Chave GSE
    No modo MAINT_WAIT, após abrir o arquivo /keys/gse_key.bin, o B/C deve
    ler exatamente 32 bytes para o buffer de chave GSE. Caso a leitura 
    retorne quantidade diferente de 32 bytes, o B/C deve registrar erro,
    fechar o arquivo e retornar o erro ESP_FAIL -1
    */
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

/* BC-LLR-20 Limpeza do buffer da chave pré-compartilhada 
O software do módulo B/C deve apagar o buffer onde as chaves do B/C 
e o GSE foram carregadas para comparação após autenticação
*/
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
    if (!keys)
    {
        ESP_LOGE(TAG, "Chaves não carregadas");
        return ESP_ERR_INVALID_ARG;
    }

    socklen_t addr_len = sizeof(*client_addr);
    tftp_packet_t packet;


    while (1)
    {
        ssize_t recv_len = recvfrom(sock, &packet, sizeof(packet), 0,
                                    (struct sockaddr *)client_addr, &addr_len);

        if (recv_len < 0)
        {
            if (errno == EAGAIN || errno == EWOULDBLOCK)
            {
                return ESP_ERR_TIMEOUT;
            }
            ESP_LOGE(TAG, "Erro ao receber chave do GSE: errno=%d", errno);
            return ESP_FAIL;
        }

        ESP_LOGI(TAG, "Iniciando handshake de autenticação");

    
        // Verifica se é um pacote DATA com a chave GSE
        if (ntohs(packet.opcode) != OP_DATA)
        {
            ESP_LOGW(TAG, "Pacote recebido não é DATA (opcode=%d), ignorando", ntohs(packet.opcode));
            continue;
        }

        // Verifica tamanho da chave
        int data_len = recv_len - 4;
        if (data_len != GSE_KEY_SIZE)
        {
            ESP_LOGW(TAG, "Tamanho da chave GSE inválido (%d bytes, esperado %d)", data_len, GSE_KEY_SIZE);
            continue;
        }

        // Verifica se a chave recebida coincide com a esperada
        if (memcmp(packet.data.data, keys->gse_verify_key, GSE_KEY_SIZE) != 0)
        {
            ESP_LOGE(TAG, "Chave GSE inválida - autenticação falhou");
            return ESP_FAIL;
        }

        ESP_LOGI(TAG, "Chave GSE válida - enviando ACK");
        break;
    }

    // Envia ACK para a chave recebida
    tftp_packet_t ack;
    ack.opcode = htons(OP_ACK);
    ack.block = packet.data.block;

    if (sendto(sock, &ack, 4, 0, (struct sockaddr *)client_addr, addr_len) < 0)
    {
        ESP_LOGE(TAG, "Erro ao enviar ACK para chave GSE: errno=%d", errno);
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

    // Passo 3: Aguarda ACK do GSE para nossa chave
    ESP_LOGI(TAG, "Aguardando confirmação da chave BC...");

    ssize_t recv_len = recvfrom(sock, &packet, sizeof(packet), 0,
                                (struct sockaddr *)client_addr, &addr_len);

    if (recv_len < 0)
    {
        if (errno == EAGAIN || errno == EWOULDBLOCK)
        {
            return ESP_ERR_TIMEOUT;
        }
        ESP_LOGE(TAG, "Erro ao receber ACK da chave BC: errno=%d", errno);
        return ESP_FAIL;
    }

    if (ntohs(packet.opcode) != OP_ACK || ntohs(packet.data.block) != 1)
    {
        ESP_LOGE(TAG, "GSE não confirmou chave BC (opcode=%d, block=%d)",
                 ntohs(packet.opcode), ntohs(packet.data.block));
        return ESP_FAIL;
    }

    ESP_LOGI(TAG, "Handshake de autenticação concluído com sucesso");
    authenticated = true;
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