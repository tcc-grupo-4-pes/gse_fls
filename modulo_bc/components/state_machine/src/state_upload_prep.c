#include "state_machine/fsm.h"
#include "esp_log.h"
#include <errno.h>

static const char *TAG = "STATE_UPLOAD_PREP";

static void state_upload_prep_enter(void)
{
    ESP_LOGI(TAG, "INIT ST_UPLOAD_PREP");
}

static fsm_state_t state_upload_prep_run(void)
{
    ESP_LOGI(TAG, "RUNNING ST_UPLOAD_PREP");

    lus_data_t lus_data;
    if (init_lus(&lus_data, ARINC_STATUS_OP_ACCEPTED_NOT_STARTED,
                 "Operation Accepted", 0, "000") != 0)
    {   
        /* BC-LLR - 54 Erro ao criar o INIT_LOAD.LUS
        No estado UPLOAD_PREP, caso haja algum erro ao criar o arquivo .LUS, 
        o software deve ir para o estado de ERROR e parar a execução */
        ESP_LOGE(TAG, "Falha ao inicializar LUS inicial");
        return ST_ERROR;
    }

    /* BC-LLR-30 Requisição de escrita do primeiro .LUS
    Em UPLOAD_PREP após envio do .LUI, o software do B/C 
    deve criar um arquivo o primeiro arquivo de status de Upload(Load Upload Status - INIT_LOAD.LUS) 
    fazer uma requisição de escrita(WRQ) para envio para GSE */
    make_wrq(sock, &client_addr, "INIT_LOAD.LUS", &lus_data);

    /* BC-LLR-32 Espera do WRQ do arquivo .LUR
    Em UPLOAD_PREP após envio do .LUS, o software do B/C 
    deve aguardar o pedido de escrita(WRQ) feito pelo GSE para obter o arquivo Load Uploading Request(.LUR) 
    para verificar o arquivo que o GSE quer carregar 
    */
    n = recvfrom(sock, &req, sizeof(req), 0,
                 (struct sockaddr *)&client_addr, &addr_len);
    if (n < 0)
    {
        ESP_LOGE(TAG, "Erro no recvfrom WRQ: errno=%d", errno);
        return ST_ERROR;
    }
    
    /* BC-LLR-56  Erro ao esperar a requisição de escrita do .LUR
    No estado UPLOAD_PREP, após o envio do primeiro .LUS, 
    caso seja recebido uma requisição que não seja de escrita do .LUR, 
    o software deve ignorar e esperar uma nova requisição */
    opcode = ntohs(req.opcode);/*BC-LLR-89*/
    if (opcode == OP_WRQ)
    {
        filename = req.request;
        // Garantir terminação de string
        filename[n - 2] = '\0';
        handle_wrq(sock, &client_addr, filename, &lur_file);

        /* BC-LLR-34 Verificação do PN
        Em UPLOAD_PREP, o software do B/C deve verificar se o PN recebido pelo arquivo 
        .LUR está presente na lista local de PNs suportados pelo módulo B/C antes de 
        iniciar o download do arquivo, se nao estiver, deve registrar e interromper execução
        */
        if (!is_pn_supported(lur_file.load_part_number))
        {   
            ESP_LOGE(TAG, "PN não suportado: %s", lur_file.load_part_number);
            return ST_ERROR;
        }

        ESP_LOGI(TAG, "PN %s verificado e suportado", lur_file.load_part_number);

        /* BC-LLR-35 Transição para UPLOADING - Requisição de leitura do firmware 
        Em UPLOAD_PREP, caso o PN for suportado pelo módulo B/C, 
        o software deve iniciar uma requisição de leitura do arquivo de nome informado no .LUR 
        e transicionar para o estado UPLOADING
        */
        return ST_UPLOADING; // Transição para uploading
    }
    else
    {
        /* BC-LLR-18*/
        ESP_LOGW(TAG, "Opcode desconhecido recebido: %d", opcode);
        return ST_ERROR;
    }
}

static void state_upload_prep_exit(void)
{
    ESP_LOGI(TAG, "EXIT ST_UPLOAD_PREP");
}

const state_ops_t state_upload_prep_ops = {
    .enter = state_upload_prep_enter,
    .run = state_upload_prep_run,
    .exit = state_upload_prep_exit,
    .name = "ST_UPLOAD_PREP"};
