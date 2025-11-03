#include "state_machine/fsm.h"
#include "esp_log.h"
#include <string.h>

static const char *TAG = "STATE_TEARDOWN";

static void state_teardown_enter(void)
{
    ESP_LOGI(TAG, "INIT ST_TEARDOWN");
}

static fsm_state_t state_teardown_run(void)
{
    ESP_LOGI(TAG, "RUNNING ST_TEARDOWN");

    // Envio do LUS final
    lus_data_t final_lus_data;
    if (init_lus(&final_lus_data, ARINC_STATUS_OP_COMPLETED_OK,
                 "Load Completed Successfully", 2, "100") != 0)
    {
        ESP_LOGE(TAG, "Falha ao inicializar LUS final");
        return ST_ERROR;
    }
    make_wrq(sock, &client_addr, "FINAL_LOAD.LUS", &final_lus_data);

    // Limpar todas variáveis globais após operação bem-sucedida
    ESP_LOGI(TAG, "Limpando variáveis globais...");

    // Zera estruturas de dados
    memset(&lur_file, 0, sizeof(lur_data_t));
    memset(hash, 0, sizeof(hash));
    memset(&req, 0, sizeof(tftp_packet_t));

    // Reseta ponteiros
    filename = NULL;
    opcode = 0;
    n = 0;
    upload_failure_count = 0;
    auth_reset_authentication(); // Reseta estado de autenticação
    
    ESP_LOGI(TAG, "Variáveis globais limpas");

    return ST_MAINT_WAIT; // Retorna para maint_wait após envio do LUS final
}

static void state_teardown_exit(void)
{
    ESP_LOGI(TAG, "EXIT ST_TEARDOWN");
}

const state_ops_t state_teardown_ops = {
    .enter = state_teardown_enter,
    .run = state_teardown_run,
    .exit = state_teardown_exit,
    .name = "ST_TEARDOWN"};
