/**
 * @file button_handler.h
 * @brief Componente para gerenciamento de botões GPIO da ESP32
 *
 * Este módulo fornece uma abstração de alto nível para configuração e monitoramento
 * de botões conectados aos pinos GPIO do ESP32. Suporta botões active-low e active-high,
 * com detecção de borda para evitar múltiplas leituras.
 *
 * Funcionalidades principais:
 * - Inicialização de botões com pull-up/pull-down automático
 * - Liberação adequada de recursos GPIO e memória
 *
 * @note Requisitos implementados: BC-LLR-5, BC-LLR-72, BC-LLR-79
 */

#ifndef BUTTON_HANDLER_H
#define BUTTON_HANDLER_H

#include <stdbool.h>
#include "driver/gpio.h"

#ifdef __cplusplus
extern "C"
{
#endif

/**
 * @brief Configuração do botão
 *
 * Estrutura usada para especificar os parâmetros de inicialização de um botão.
 * Define o pino GPIO e a lógica de ativação (active-low ou active-high).
 */
typedef struct
{
    gpio_num_t gpio_num; /**< Número do GPIO onde o botão está conectado */
    bool active_low;     /**< true se botão ativo em nível baixo (pull-up), false se active-high */
} button_config_t;

/**
 * @brief Handle do botão (opaco)
 *
 * Ponteiro opaco para a estrutura interna de gerenciamento do botão.
 * Não deve ser acessado diretamente - use as funções da API.
 */
typedef struct button_handle_s *button_handle_t;

/**
 * @brief Inicializa um botão GPIO
 *
 * Aloca memória e configura o GPIO especificado para operar como entrada.
 * Automaticamente habilita pull-up (se active_low) ou pull-down (se active_high).
 *
 * @param[in] config Configuração do botão (GPIO e lógica de ativação)
 * @param[out] handle Ponteiro para receber o handle do botão inicializado
 *
 * @return
 *     - ESP_OK: Botão inicializado com sucesso
 *     - ESP_ERR_INVALID_ARG: Parâmetros inválidos (config ou handle NULL)
 *     - ESP_ERR_NO_MEM: Falha ao alocar memória para o handle
 *     - Outros códigos de erro retornados por gpio_config()
 *
 * @note BC-LLR-5, BC-LLR-79
 */
esp_err_t button_init(const button_config_t *config, button_handle_t *handle);

/**
 * @brief Verifica se o botão foi pressionado (non-blocking)
 *
 * Lê o estado atual do GPIO e detecta transições de borda (não-pressionado -> pressionado).
 * Retorna true apenas na primeira detecção do pressionamento, evitando múltiplas leituras
 * enquanto o botão permanece pressionado.
 *
 * @param[in] handle Handle do botão retornado por button_init()
 *
 * @return
 *     - true: Botão acabou de ser pressionado (borda de subida/descida detectada)
 *     - false: Botão não foi pressionado ou handle inválido
 *
 * @note BC-LLR-5: Detecção de pressionamento com controle de estado
 * @note Esta função deve ser chamada periodicamente em um loop ou task
 */
bool button_is_pressed(button_handle_t handle);

/**
 * @brief Libera recursos do botão
 *
 * Reseta o GPIO para o estado padrão e libera a memória alocada para o handle.
 * Deve ser chamado quando o botão não é mais necessário para evitar vazamento de recursos.
 *
 * @param[in] handle Handle do botão a ser liberado
 *
 * @return
 *     - ESP_OK: Recursos liberados com sucesso
 *     - ESP_ERR_INVALID_ARG: Handle inválido (NULL)
 *
 * @note BC-LLR-72: Liberação de recursos do botão na saída do modo operacional
 * @warning Após chamar esta função, o handle não deve mais ser usado
 */
esp_err_t button_deinit(button_handle_t handle);

/**
 * @brief Configuração padrão para o botão BOOT (GPIO0)
 */
#define BUTTON_BOOT_DEFAULT_CONFIG() { \
    .gpio_num = GPIO_NUM_0,            \
    .active_low = true}

#ifdef __cplusplus
}
#endif

#endif /* BUTTON_HANDLER_H */