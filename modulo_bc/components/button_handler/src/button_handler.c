/**
 * @file button_handler.c
 * @brief Implementação do componente de gerenciamento de botões GPIO
 *
 * Este arquivo implementa as funções de alto nível para inicialização,
 * monitoramento e liberação de recursos de botões GPIO no ESP32.
 *
 * @note Requisitos implementados: BC-LLR-5, BC-LLR-72, BC-LLR-79
 */

#include "button_handler/button_handler.h"
#include "esp_log.h"
#include "esp_err.h"
#include <stdlib.h>

static const char *TAG = "BUTTON_HANDLER";

/**
 * @brief Estrutura interna do handle do botão
 *
 * Contém informações de configuração e estado para gerenciamento do botão.
 */
struct button_handle_s
{
    gpio_num_t gpio_num; /**< Número do GPIO configurado */
    bool active_low;     /**< true se botão é active-low (lógica invertida) */
    bool last_state;     /**< Estado anterior do botão (para detecção de borda) */
};

/**
 * @brief Inicializa um botão GPIO
 *
 * Aloca memória para o handle do botão, configura o GPIO especificado como entrada
 * e habilita pull-up/pull-down apropriado baseado na lógica do botão (active-low/high).
 * Em caso de erro na configuração GPIO, libera recursos alocados antes de retornar.
 *
 * @param[in] config Ponteiro para configuração do botão (GPIO e lógica)
 * @param[out] handle Ponteiro para receber o handle do botão inicializado
 *
 * @return
 *     - ESP_OK: Botão inicializado com sucesso
 *     - ESP_ERR_INVALID_ARG: Parâmetros inválidos (config ou handle NULL)
 *     - ESP_ERR_NO_MEM: Falha ao alocar memória
 *     - Outros: Código de erro retornado por gpio_config()
 *
 * @note BC-LLR-5, BC-LLR-79
 */
esp_err_t button_init(const button_config_t *config, button_handle_t *handle)
{
    if (!config || !handle)
    {
        ESP_LOGE(TAG, "Parâmetros inválidos");
        return ESP_ERR_INVALID_ARG;
    }

    /* BC-LLR-5 - Alocar handle */
    struct button_handle_s *btn = malloc(sizeof(struct button_handle_s));
    if (!btn)
    {
        ESP_LOGE(TAG, "Falha ao alocar memória para handle do botão");
        return ESP_ERR_NO_MEM;
    }

    /* BC-LLR-5 */
    btn->gpio_num = config->gpio_num;
    btn->active_low = config->active_low;
    btn->last_state = false;

    // Configurar GPIO
    gpio_config_t gpio_cfg = {
        .pin_bit_mask = (1ULL << config->gpio_num),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = config->active_low ? GPIO_PULLUP_ENABLE : GPIO_PULLUP_DISABLE,
        .pull_down_en = config->active_low ? GPIO_PULLDOWN_DISABLE : GPIO_PULLDOWN_ENABLE,
        .intr_type = GPIO_INTR_DISABLE};

    esp_err_t ret = gpio_config(&gpio_cfg);

    /* BC-LLR-79 Validação de configuração GPIO botão
    No modo INIT, em caso de erro na configuração do GPIO do botão,
    o B/C deve liberar recursos alocados para o botão e retornar -1
    */
    if (ret != ESP_OK)
    {
        ESP_LOGE(TAG, "Falha ao configurar GPIO%d: %s", config->gpio_num, esp_err_to_name(ret));
        free(btn);
        return ret;
    }

    *handle = btn;
    ESP_LOGI(TAG, "Botão inicializado no GPIO%d (active_low=%s)",
             config->gpio_num, config->active_low ? "true" : "false");

    return ESP_OK;
}

/**
 * @brief Verifica se o botão foi pressionado (detecção de borda)
 *
 * Lê o nível do GPIO e detecta transições de estado (não-pressionado -> pressionado).
 * Retorna true apenas na primeira detecção do pressionamento, evitando múltiplas
 * leituras enquanto o botão permanece pressionado. Implementa debounce por software
 * através de rastreamento do último estado.
 *
 * @param[in] handle Handle do botão retornado por button_init()
 *
 * @return
 *     - true: Botão acabou de ser pressionado (borda detectada)
 *     - false: Botão não foi pressionado, já estava pressionado, ou handle inválido
 *
 * @note BC-LLR-5
 */
bool button_is_pressed(button_handle_t handle)
{
    if (!handle)
    {
        return false;
    }

    /* BC-LLR-5 */
    int current_level = gpio_get_level(handle->gpio_num);
    bool is_active = handle->active_low ? (current_level == 0) : (current_level == 1);

    /* BC-LLR-5 */
    if (is_active && !handle->last_state)
    {
        handle->last_state = true;
        ESP_LOGI(TAG, "Botão GPIO%d pressionado", handle->gpio_num);
        return true;
    }
    else if (!is_active)
    {
        handle->last_state = false;
    }

    return false;
}

/**
 * @brief Libera recursos do botão
 *
 * Reseta o GPIO para o estado padrão e libera a memória alocada para o handle.
 * Esta função deve ser chamada quando o botão não é mais necessário para evitar
 * vazamento de recursos. Após chamar esta função, o handle não deve mais ser usado.
 *
 * @param[in] handle Handle do botão a ser liberado
 *
 * @return
 *     - ESP_OK: Recursos liberados com sucesso
 *     - ESP_ERR_INVALID_ARG: Handle inválido (NULL)
 *
 * @note BC-LLR-72
 */
esp_err_t button_deinit(button_handle_t handle)
{
    /* BC-LLR-72 - Liberação de recursos do botão
    Na saída do modo operacional, o B/C deve liberar todos os recursos associados ao botão de manutenção
    (GPIO, handlers, memória) para evitar vazamento de recursos e garantir que o botão não influencie na manutenção
    */
    if (!handle)
    {
        return ESP_ERR_INVALID_ARG;
    }

    ESP_LOGI(TAG, "Liberando recursos do botão GPIO%d", handle->gpio_num);

    // Reset do GPIO para estado padrão
    gpio_reset_pin(handle->gpio_num);

    // Liberar memória
    free(handle);

    return ESP_OK;
}
