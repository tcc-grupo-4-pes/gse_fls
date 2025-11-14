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

    /*BC-LLR-106 - Requisição de escrita do último .LUS
    Em TEARDOWN, o software do B/C deve criar um arquivo do último status de Upload,
    (Load Upload Status - FINAL.LUS) fazer uma requisição de escrita(WRQ) para envio para GSE */
    lus_data_t final_lus_data;
    if (init_lus(&final_lus_data, ARINC_STATUS_OP_COMPLETED_OK,
                 "Load Completed Successfully", 2, "100") != 0)
    {
        /* BC-LLR-68 Erro ao inicializar o FINAL.LUS
        No estado TEARDOWN, caso haja algum erro ao inicializar o arquivo FINAL.LUS,
        o software deve ir para o estado ERROR e parar a execução da tarefa*/
        ESP_LOGE(TAG, "Falha ao inicializar LUS final");
        return ST_ERROR;
    }
    make_wrq(sock, &client_addr, "FINAL_LOAD.LUS", &final_lus_data);

    /* BC-LLR-47 */
    state_teardown_reset_globals();

    /* BC-LLR-48 Transição para estado MAINT_WAIT partindo do TEARDOWN
    No estado TEARDOWN, após todas finalizações terem sido completas corretamente,
    o software do B/C deve transicionar para o estado MAINT_WAIT para possibilitar que o processo de carregamento possa ser repetido
    */
    return ST_MAINT_WAIT;
}

void state_teardown_reset_globals(void)
{
    /* BC-LLR-47 Limpeza das variáveis globais
    No estado TEARDOWN, o software do B/C deve limpar todas variáveis globais como:
    a estrutura do .LUR, o hash, o pacote TFTP que contém as requisições,
    deve resetar ponteiros, opcode, contador de falhas e resetar a autenticação
    */
    ESP_LOGI(TAG, "Limpando variáveis globais...");

    memset(&lur_file, 0, sizeof(lur_data_t));
    memset(hash, 0, sizeof(hash));
    memset(&req, 0, sizeof(tftp_packet_t));

    filename = NULL;
    opcode = 0;
    n = 0;
    upload_failure_count = 0;
    auth_reset_authentication();

    ESP_LOGI(TAG, "Variáveis globais limpas");
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
