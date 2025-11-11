#include <stdio.h>
#include "unity.h"
#include "esp_task_wdt.h"
#include "esp_vfs_dev.h"
#include "driver/uart.h"

void app_main(void)
{
    printf("Iniciando testes do componente auth e state_machine...\n");

    // Desativa o watchdog para evitar reset durante o menu interativo do Unity
    esp_task_wdt_deinit();

    // Garante que o console utilize o driver UART antes de rodar o menu Unity
    const int uart_num = CONFIG_ESP_CONSOLE_UART_NUM;
    uart_driver_install(uart_num, 256, 0, 0, NULL, 0);
    esp_vfs_dev_uart_use_driver(uart_num);

    unity_run_menu();
}