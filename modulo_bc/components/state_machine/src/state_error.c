/**
 * @file state_error.c
 * @brief Implementação do estado ERROR da máquina de estados
 *
 * Estado terminal que remove arquivos temporários e encerra a execução do sistema
 * após detectar erro irrecuperável.
 *
 * @note BC-LLR-105
 */

#include "state_machine/fsm.h"
#include "esp_log.h"
#include "storage.h"
#include <errno.h>
#include <unistd.h> // unlink

static const char *TAG = "STATE_ERROR";

/**
 * @brief Função de entrada do estado ERROR
 *
 * Executa log de entrada no estado (atualmente apenas informação).
 */
static void state_error_enter(void)
{
    ESP_LOGI(TAG, "INIT ST_ERROR");
}

/**
 * @brief Função de execução do estado ERROR
 *
 * Estado terminal de erro que:
 * 1. Remove arquivo temporário temp.bin (se existir)
 * 2. Registra mensagem de erro fatal
 * 3. Encerra a execução do sistema com abort()
 *
 * Este estado não retorna - o sistema é finalizado.
 *
 * @return ST_ERROR (nunca é alcançado devido ao abort())
 *
 * @note BC-LLR-105
 */
static fsm_state_t state_error_run(void)
{
    /* BC-LLR-105 Exclusão do arquivo temporário quando em erro
    No estado ERROR, o software deve excluir o arquivo temp.bin da memória flash caso ele exista */
    int rc = unlink(TEMP_FILE_PATH);
    if (rc == 0)
    {
        ESP_LOGI(TAG, "Firmware temporario removido: %s", TEMP_FILE_PATH);
    }
    else
    {
        ESP_LOGW(TAG, "Nao foi possivel remover %s (errno=%d)", TEMP_FILE_PATH, errno);
    }

    ESP_LOGE(TAG, "SISTEMA EM ESTADO DE ERRO - EXECUÇÃO INTERROMPIDA");

    // Para o funcionamento do ESP
    abort();

    return ST_ERROR;
}

/**
 * @brief Função de saída do estado ERROR
 *
 * Nunca é chamada pois o estado ERROR encerra a execução com abort().
 */
static void state_error_exit(void)
{
    ESP_LOGI(TAG, "EXIT ST_ERROR");
}

const state_ops_t state_error_ops = {
    .enter = state_error_enter,
    .run = state_error_run,
    .exit = state_error_exit,
    .name = "ST_ERROR"};