/**
 * @file state_verify.c
 * @brief Implementação do estado VERIFY da máquina de estados
 *
 * Estado que compara o SHA-256 calculado durante o recebimento do firmware
 * com o SHA-256 esperado enviado pelo GSE para verificar a integridade.
 *
 * @note BC-LLR-42, BC-LLR-43, BC-LLR-65, BC-LLR-103
 */

#include "state_machine/fsm.h"
#include "esp_log.h"
#include <string.h>
#include <storage.h>
static const char *TAG = "STATE_VERIFY";

/**
 * @brief Função de entrada do estado VERIFY
 *
 * Executa log de entrada no estado (atualmente apenas informação).
 */
static void state_verify_enter(void)
{
    ESP_LOGI(TAG, "INIT ST_VERIFY");
}

/**
 * @brief Função de execução do estado VERIFY
 *
 * Compara o SHA-256 calculado durante o download do firmware com o SHA-256
 * esperado recebido do GSE. Valida a integridade do firmware recebido.
 *
 * @return Próximo estado da FSM:
 *         - ST_SAVE: hashes coincidem, firmware íntegro
 *         - ST_ERROR: hashes diferentes, firmware corrompido
 *
 * @note BC-LLR-42, BC-LLR-43, BC-LLR-65
 */
static fsm_state_t state_verify_run(void)
{
    ESP_LOGI(TAG, "RUNNING ST_VERIFY");

    // Verificação de PN movida para o primeiro pacote de dados em make_rrq (tftp.c)
    /* BC-LLR-42 - No estado VERIFY, com o SHA256 esperado recebido e o SHA256 calculado durante o recebimento do firmware,
    o software do B/C deve compará-los e verificação se são iguais para atestar integridade do recebimento do firmware
    */
    if (memcmp(req.data.data, hash, 32) != 0)
    {
        /* BC-LLR-65 - Erro de integridade - SHA256 diferente
        No estado VERIFY, caso o SHA256 calculado não seja igual ao recebido do GSE,
        o software deve ir para o estado ERROR e parar a execução da tarefa*/
        ESP_LOGE(TAG, "Hash SHA-256 não confere! Arquivo corrompido.");
        return ST_ERROR;
    }
    else
    {
        /* BC-LLR-43 - Transição para estado SAVE
        No estado VERIFY, com a integridade verificada,
        o software do B/C deve transicionar do estado para o estado SAVE
        */
        ESP_LOGI(TAG, "Hash SHA-256 conferido com sucesso.");
        return ST_SAVE; // Hash OK, prosseguir para salvar
    }
}

/**
 * @brief Função de saída do estado VERIFY
 *
 * Executa limpeza ao sair do estado (atualmente apenas log).
 */
static void state_verify_exit(void)
{
    ESP_LOGI(TAG, "EXIT ST_VERIFY");
}

const state_ops_t state_verify_ops = {
    .enter = state_verify_enter,
    .run = state_verify_run,
    .exit = state_verify_exit,
    .name = "ST_VERIFY"};
