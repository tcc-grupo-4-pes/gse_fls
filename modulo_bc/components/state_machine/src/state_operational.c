#include "state_machine/fsm.h"
#include "button_handler/button_handler.h"
#include "esp_log.h"

static const char *TAG = "STATE_OPERATIONAL";

// Handle do botão (será inicializado no enter)
static button_handle_t maint_button = NULL;

static void state_operational_enter(void)
{
    ESP_LOGI(TAG, "INIT ST_OPERATIONAL");

    /* BC-LLR-5 - Configuração botão de manutenção 
    Na entrada do modo operational, o sistema deve configurar o botão de manutenção para detectar aperto 
    (transição de solto para pressionado), usando a configuração padrão do botão.*/
    button_config_t button_config = BUTTON_BOOT_DEFAULT_CONFIG();
    esp_err_t ret = button_init(&button_config, &maint_button);

    if (ret == ESP_OK)
    {
        ESP_LOGI(TAG, "Botão de manutenção configurado - pressione para entrar no modo manutenção");
    }
    else
    {
        ESP_LOGE(TAG, "Falha ao configurar botão de manutenção: %s", esp_err_to_name(ret));
        maint_button = NULL;
    }
}

static fsm_state_t state_operational_run(void)
{
    ESP_LOGI(TAG, "RUNNING ST_OPERATIONAL");
    /* BC-LLR-4 - Botão para ir para modo Manutenção
    Em modo OPERACIONAL, o software do B/C deve mudar para o modo MANUTENÇÃO (estado MAINT_WAIT) 
    se o botão (GPIO 0) do ESP32 for apertado.
    */
    if (maint_button && button_is_pressed(maint_button))
    {
        ESP_LOGI(TAG, "Botão de manutenção pressionado - transitando para modo manutenção");
        return ST_MAINT_WAIT;
    }

    // Continuar no modo operacional
    return ST_OPERATIONAL;
}

static void state_operational_exit(void)
{
    ESP_LOGI(TAG, "EXIT ST_OPERATIONAL");

    /* BC-LLR-73 - Na saída do modo operacional, 
    o B/C deve liberar todos os recursos associados ao botão de manutenção (GPIO, handlers, memória ) 
    para evitar vazamento de recursos e garantir que o botão mão influencie na manutenção */
    if (maint_button)
    {
        button_deinit(maint_button);
        maint_button = NULL;
        ESP_LOGI(TAG, "Recursos do botão liberados");
    }
}

const state_ops_t state_operational_ops = {
    .enter = state_operational_enter,
    .run = state_operational_run,
    .exit = state_operational_exit,
    .name = "ST_OPERATIONAL"};