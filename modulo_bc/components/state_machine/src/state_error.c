#include "state_machine/fsm.h"
#include "esp_log.h"
#include "storage.h"
#include <unistd.h> // unlink

static const char *TAG = "STATE_ERROR";

static void state_error_enter(void)
{
    ESP_LOGI(TAG, "INIT ST_ERROR");
}

static fsm_state_t state_error_run(void)
{
    unlink(TEMP_FILE_PATH);
    ESP_LOGE(TAG, "SISTEMA EM ESTADO DE ERRO - EXECUÇÃO INTERROMPIDA");

    // Para o funcionamento do ESP
    abort();

    return ST_ERROR;
}

static void state_error_exit(void)
{
    ESP_LOGI(TAG, "EXIT ST_ERROR");
}

const state_ops_t state_error_ops = {
    .enter = state_error_enter,
    .run = state_error_run,
    .exit = state_error_exit,
    .name = "ST_ERROR"};