#include "button_handler/button_handler.h"
#include "esp_log.h"
#include "esp_err.h"
#include <stdlib.h>

static const char *TAG = "BUTTON_HANDLER";

/**
 * @brief Estrutura interna do handle do botão
 */
struct button_handle_s
{
    gpio_num_t gpio_num;
    bool active_low;
    bool last_state;
};

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

/* BC-LLR-73 - Liberação de recursos do botão */
esp_err_t button_deinit(button_handle_t handle)
{
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
