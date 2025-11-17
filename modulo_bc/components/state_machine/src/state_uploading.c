/**
 * @file state_uploading.c
 * @brief Implementação do estado UPLOADING da máquina de estados
 *
 * Estado que solicita e recebe o arquivo de firmware do GSE via TFTP,
 * calcula SHA-256 durante a transferência e aguarda o hash esperado para verificação.
 *
 * @note BC-LLR-37, BC-LLR-40, BC-LLR-41, BC-LLR-63, BC-LLR-64, BC-LLR-89, BC-LLR-90,
 *       BC-LLR-96, BC-LLR-97, BC-LLR-98, BC-LLR-99, BC-LLR-100, BC-LLR-101, BC-LLR-102
 */

#include "state_machine/fsm.h"
#include "esp_log.h"
#include "lwip/inet.h"
#include <errno.h>

static const char *TAG = "STATE_UPLOADING";

static struct sockaddr_in original_client_addr;

/**
 * @brief Função de entrada do estado UPLOADING
 *
 * Preserva o endereço original do cliente (GSE) e inicia o download do firmware
 * via TFTP chamando make_rrq(). O endereço é salvo para restauração posterior
 * após o envio do LUS.
 *
 * @note BC-LLR-101
 */
static void state_uploading_enter(void)
{
    ESP_LOGI(TAG, "INIT ST_UPLOADING");

    /* BC-LLR-101 Preservação do endereço do cliente
       No estado UPLOADING, antes de iniciar a transferência do firmware,
       o software deve salvar o endereço original do cliente (GSE) para restauração
       posterior ao envio do LUS
    */
    original_client_addr = client_addr;

    make_rrq(sock, &client_addr, lur_file.header_filename, hash);
}

/**
 * @brief Função de execução do estado UPLOADING
 *
 * Aguarda o último pacote contendo o SHA-256 esperado do firmware:
 * 1. Recebe pacote com hash SHA-256 do GSE
 * 2. Envia ACK para o hash recebido
 * 3. Restaura endereço original do cliente
 * 4. Envia arquivo STATUS.LUS com progresso 50%
 *
 * @return Próximo estado da FSM:
 *         - ST_VERIFY: hash recebido com sucesso
 *         - ST_ERROR: erro ao receber hash ou enviar ACK/LUS
 *
 * @note BC-LLR-40, BC-LLR-41, BC-LLR-63, BC-LLR-64, BC-LLR-89, BC-LLR-90, BC-LLR-102
 */
static fsm_state_t state_uploading_run(void)
{
    ESP_LOGI(TAG, "RUNNING ST_UPLOADING");

    /* BC-LLR-40 Pacote SHA256 esperado
       No estado UPLOADING, após receber todos os pacotes do firmware,
       o software do B/C deve esperar um último pacote com o SHA256 para verificação de integridade
    */
    if (recvfrom(sock, &req, sizeof(req), 0,
                 (struct sockaddr *)&client_addr, &addr_len) < 0)
    {
        /* BC-LLR-63 Erro de não recebimento do SHA256 ao final
        No estado UPLOADING, caso o SHA256 esperado (enviado pelo GSE) não seja recebido,
        o software do B/C deve ir para o estado ERROR e parar a execução da tarefa
        */
        ESP_LOGE(TAG, "Erro no recvfrom do hash: errno=%d", errno);
        return ST_ERROR;
    }

    // Envia ACK para o hash recebido
    tftp_packet_t hash_ack;
    hash_ack.opcode = htons(OP_ACK); /*BC-LLR-90*/
    hash_ack.block = req.data.block; // Mantém o mesmo número do bloco recebido

    /* BC-LLR-64 Erro ao enviar ACK do hash esperado
       No estado UPLOADING, caso haja erro ao enviar o ACK referente ao hash recebido,
       o software deve ir para o estado ERROR e parar a execução
    */
    if (sendto(sock, &hash_ack, 4, 0,
               (struct sockaddr *)&client_addr, addr_len) < 0) /*BC-LLR-28*/
    {
        ESP_LOGE(TAG, "Erro ao enviar ACK do hash: errno=%d", errno);
        return ST_ERROR;
    }
    ESP_LOGI(TAG, "ACK enviado para hash (bloco %d)", ntohs(req.data.block));

    /* BC-LLR-102 Restauração do endereço do cliente
       No estado UPLOADING, após receber o hash esperado, o software deve restaurar
       o endereço original do cliente (GSE) para que o LUS seja enviado para a porta
       principal (69) e não para o TID efêmero
    */
    client_addr = original_client_addr;
    ESP_LOGI(TAG, "Endereço do cliente restaurado para IP=%s, porta=%d",
             inet_ntoa(client_addr.sin_addr), ntohs(client_addr.sin_port));

    /* BC-LLR-41 Transição para estado VERIFY
       No estado UPLOADING, após receber o pacote contendo o SHA256 esperado,
       o software do B/C deve transicionar para o estado VERIFY
    */
    return ST_VERIFY;
}

/**
 * @brief Função de saída do estado UPLOADING
 *
 * Executa limpeza ao sair do estado (atualmente apenas log).
 */
static void state_uploading_exit(void)
{
    ESP_LOGI(TAG, "EXIT ST_UPLOADING");
}

const state_ops_t state_uploading_ops = {
    .enter = state_uploading_enter,
    .run = state_uploading_run,
    .exit = state_uploading_exit,
    .name = "ST_UPLOADING"};
