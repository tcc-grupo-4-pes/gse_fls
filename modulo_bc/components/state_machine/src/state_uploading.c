#include "state_machine/fsm.h"
#include "esp_log.h"
#include "lwip/inet.h"
#include <errno.h>

static const char *TAG = "STATE_UPLOADING";

static struct sockaddr_in original_client_addr;

static void state_uploading_enter(void)
{
    ESP_LOGI(TAG, "INIT ST_UPLOADING");

    // Faz um RRQ para obter o arquivo com o nome obtido do LUR
    // CORREÇÃO: Salva o endereço original do cliente antes de make_rrq
    // porque make_rrq modifica client_addr para o TID efêmero do servidor
    original_client_addr = client_addr;

    make_rrq(sock, &client_addr, lur_file.header_filename, hash);
}

static fsm_state_t state_uploading_run(void)
{
    ESP_LOGI(TAG, "RUNNING ST_UPLOADING");

    // Receber o hash com tftp e comparar com o calculado
    // Hash vem do TID efêmero que make_rrq detectou
    if (recvfrom(sock, &req, sizeof(req), 0,
                 (struct sockaddr *)&client_addr, &addr_len) < 0)
    {
        ESP_LOGE(TAG, "Erro no recvfrom do hash: errno=%d", errno);
        return ST_ERROR;
    }

    // Envia ACK para o hash recebido
    tftp_packet_t hash_ack;
    hash_ack.opcode = htons(OP_ACK);
    hash_ack.block = req.data.block; // Mantém o mesmo número do bloco recebido
    if (sendto(sock, &hash_ack, 4, 0,
               (struct sockaddr *)&client_addr, addr_len) < 0)
    {
        ESP_LOGE(TAG, "Erro ao enviar ACK do hash: errno=%d", errno);
        return ST_ERROR;
    }
    ESP_LOGI(TAG, "ACK enviado para hash (bloco %d)", ntohs(req.data.block));

    // CORREÇÃO: Restaura endereço original do cliente para envio de LUS
    // LUS deve ser enviado para o socket principal do GSE, não para o TID efêmero
    client_addr = original_client_addr;
    ESP_LOGI(TAG, "Endereço do cliente restaurado para IP=%s, porta=%d",
             inet_ntoa(client_addr.sin_addr), ntohs(client_addr.sin_port));

    return ST_VERIFY; // Transição para verificação do hash
}

static void state_uploading_exit(void)
{
    ESP_LOGI(TAG, "EXIT ST_UPLOADING");
}

const state_ops_t state_uploading_ops = {
    .enter = state_uploading_enter,
    .run = state_uploading_run,
    .exit = state_uploading_exit,
    .name = "ST_UPLOADING"};
