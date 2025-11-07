#include "state_machine/fsm.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "storage.h"
#include "auth.h"

static const char *TAG = "STATE_INIT";

static void state_init_enter(void)
{
    ESP_LOGI(TAG, "ENTER ST_INIT");
}
static fsm_state_t state_init_run(void)
{
    ESP_LOGI(TAG, "RUN ST_INIT ");

    /* BC-LLR-2 - Inicializações do estado INIT
    No modo INIT, o software deve executar, sequencialmente 
    (A) Iniciar NVS 
    (B) Inicializar SPIFFs 
    (C) Escrever chaves estática de autenticação;
    */
    /* (A) Inicializar NVS */
    nvs_flash_init();

    /* (B) Inicializar SPIFFs*/
    esp_err_t spiffs_ret_firmware = mount_spiffs("firmware", FIRMWARE_MOUNT_POINT);
    esp_err_t spiffs_ret_keys = mount_spiffs("keys", KEYS_MOUNT_POINT);
    
    /* BC-LLR-3 - Tratamento de erros na inicialização do SPIFFS
    No estado INIT caso haja erro ao montar a partição, 
    o software deve ir para o estado de ERROR e parar a execução
    */
    if (spiffs_ret_firmware != ESP_OK)
    {
        ESP_LOGE(TAG, "Falha ao montar partição 'firmware': %s", esp_err_to_name(spiffs_ret_firmware));
        return ST_ERROR;
    }

    if (spiffs_ret_keys != ESP_OK)
    {
        ESP_LOGE(TAG, "Falha ao montar partição 'keys': %s", esp_err_to_name(spiffs_ret_keys));
        return ST_ERROR;
    }

    ESP_LOGI(TAG, "Partições SPIFFS montadas com sucesso");

    /* BC-LLR-50 - Partição com chaves de autenticação
    A partição keys deve conter as chaves pré-compartilhadas para verificação de autenticidade do GSE bem como
    as chaves enviadas ao GSE para autenticar o BC como aplicação Embraer*/
    if (auth_write_static_keys() != ESP_OK)
    {
        ESP_LOGE(TAG, "Falha ao escrever chaves de autenticação");
        return ST_ERROR;
    }

    /* BC-LLR-1 - Início no modo operacional
    Ao boot, o módulo B/C deve inicializar o estado INIT e, 
    após verificações (ver BC-LLR-2) migrar automaticamente para OPERATIONAL 
    se não houver sinalização de manutenção
    */
    ESP_LOGI(TAG, "Inicialização completa - transição para ST_OPERATIONAL");

    return ST_OPERATIONAL;
}

static void state_init_exit(void)
{
    ESP_LOGI(TAG, "EXIT ST_INIT");
}

const state_ops_t state_init_ops = {
    .enter = state_init_enter,
    .run = state_init_run,
    .exit = state_init_exit,
    .name = "ST_INIT"};
