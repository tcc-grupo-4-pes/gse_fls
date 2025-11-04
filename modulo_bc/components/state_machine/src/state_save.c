#include "state_machine/fsm.h"
#include "esp_log.h"
#include "storage.h"

static const char *TAG = "STATE_SAVE";

static void state_save_enter(void)
{
    ESP_LOGI(TAG, "INIT ST_SAVE");
}

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

static void state_save_exit(void)
{
    ESP_LOGI(TAG, "EXIT ST_SAVE");
}

const state_ops_t state_save_ops = {
    .enter = state_save_enter,
    .run = state_save_run,
    .exit = state_save_exit,
    .name = "ST_SAVE"};
