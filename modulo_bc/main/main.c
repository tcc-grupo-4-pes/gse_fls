#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "state_machine/fsm.h"

static const char* TAG = "APP_MAIN";

void app_main(void)
{
    ESP_LOGI(TAG, "Iniciando aplicação B/C");

    ESP_LOGI(TAG, "Iniciando máquina de estados");
    bc_fsm_start();  
    
}
