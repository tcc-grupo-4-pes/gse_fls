/**
 * @file state_save.c
 * @brief Implementação do estado SAVE da máquina de estados
 *
 * Estado que finaliza o arquivo de firmware renomeando temp.bin para final.bin
 * após verificação bem-sucedida de integridade.
 *
 * @note BC-LLR-44, BC-LLR-45, BC-LLR-46, BC-LLR-66, BC-LLR-67
 */

#include "state_machine/fsm.h"
#include "esp_log.h"
#include "storage.h"

static const char *TAG = "STATE_SAVE";

/**
 * @brief Função de entrada do estado SAVE
 *
 * Executa log de entrada no estado (atualmente apenas informação).
 */
static void state_save_enter(void)
{
    ESP_LOGI(TAG, "INIT ST_SAVE");
}

/**
 * @brief Função de execução do estado SAVE
 *
 * Finaliza o arquivo de firmware renomeando temp.bin para final.bin.
 * Remove o arquivo final.bin anterior (se existir) antes da renomeação.
 *
 * @return Próximo estado da FSM:
 *         - ST_TEARDOWN: arquivo salvo com sucesso
 *         - ST_ERROR: falha ao renomear arquivo
 *
 * @note BC-LLR-44, BC-LLR-45, BC-LLR-46, BC-LLR-66, BC-LLR-67
 */
static fsm_state_t state_save_run(void)
{
    ESP_LOGI(TAG, "RUNNING ST_SAVE");

    /* BC-LLR-44 e BC-LLR-45 - Finaliza e renomeia arquivo de firmware */
    /* BC-LLR-66 e BC-LLR-67 - Erros ao finalizar e renomear arquivo de firmware */
    if (finalize_firmware_file() != ESP_OK)
    {
        ESP_LOGE(TAG, "Falha ao finalizar arquivo de firmware");
        return ST_ERROR;
    }

    /* BC-LLR46 - Transição para estado TEARDOWN
    No estado SAVE, caso a operação de renomear
    e o arquivo de firmware for devidamente armazenado na partição fs_main como final.bin,
    o software do B/C deve transicionar para o estado TEARDOWN
    */
    return ST_TEARDOWN;
}

/**
 * @brief Função de saída do estado SAVE
 *
 * Executa limpeza ao sair do estado (atualmente apenas log).
 */
static void state_save_exit(void)
{
    ESP_LOGI(TAG, "EXIT ST_SAVE");
}

const state_ops_t state_save_ops = {
    .enter = state_save_enter,
    .run = state_save_run,
    .exit = state_save_exit,
    .name = "ST_SAVE"};
