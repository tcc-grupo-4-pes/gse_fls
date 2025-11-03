/**
 * @file button_handler.h
 * @brief Componente para gerenciamento de botões da ESP32
 */

#ifndef BUTTON_HANDLER_H
#define BUTTON_HANDLER_H

#include <stdbool.h>
#include "driver/gpio.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Configuração do botão
 */
typedef struct {
    gpio_num_t gpio_num;           // Número do GPIO
    bool active_low;               // true se botão ativo em nível baixo
} button_config_t;

/**
 * @brief Handle do botão (opaco)
 */
typedef struct button_handle_s* button_handle_t;

/**
 * @brief Inicializa um botão
 * @param config Configuração do botão
 * @param handle Ponteiro para receber o handle do botão
 * @return ESP_OK se sucesso, erro caso contrário
 */
esp_err_t button_init(const button_config_t *config, button_handle_t *handle);

/**
 * @brief Verifica se o botão foi pressionado (non-blocking)
 * @param handle Handle do botão
 * @return true se botão foi pressionado e validado, false caso contrário
 */
bool button_is_pressed(button_handle_t handle);

/**
 * @brief Libera recursos do botão
 * @param handle Handle do botão
 * @return ESP_OK se sucesso
 */
esp_err_t button_deinit(button_handle_t handle);

/**
 * @brief Configuração padrão para o botão BOOT (GPIO0)
 */
#define BUTTON_BOOT_DEFAULT_CONFIG() { \
    .gpio_num = GPIO_NUM_0, \
    .active_low = true \
}

#ifdef __cplusplus
}
#endif

#endif /* BUTTON_HANDLER_H */