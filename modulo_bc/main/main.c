/**
 * @file main.c
 * @brief Ponto de entrada principal da aplicação B/C
 *
 * Este arquivo contém a função app_main() que serve como ponto de entrada
 * da aplicação do módulo B/C. A função inicializa
 * a máquina de estados principal que gerencia todos os modos de operação
 * do sistema (operacional, manutenção, upload de firmware).
 *
 * @note BC-LLR-1
 */

#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "state_machine/fsm.h"

static const char *TAG = "APP_MAIN"; /**< Tag para logging */

/**
 * @brief Ponto de entrada principal da aplicação B/C
 *
 * Função chamada automaticamente pelo ESP-IDF após inicialização do hardware.
 * Responsável por iniciar a máquina de estados (FSM) do módulo B/C, que gerencia
 * o ciclo de vida completo da aplicação incluindo:
 * - Inicialização de subsistemas (NVS, SPIFFS, chaves)
 * - Modo operacional normal
 * - Modo de manutenção com carregamento de firmware via TFTP
 *
 * Esta função não retorna - a FSM executa em loop infinito até erro fatal.
 *
 * @note BC-LLR-1
 */
void app_main(void)
{
    ESP_LOGI(TAG, "Iniciando aplicação B/C");

    ESP_LOGI(TAG, "Iniciando máquina de estados");
    bc_fsm_start();
}
