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
        ESP_LOGE(TAG, "Falha ao inicializar LUS inicial");
        return ST_ERROR;
    }

    make_wrq(sock, &client_addr, "INIT_LOAD.LUS", &lus_data);

    // Aguarda um write request do GSE para escrita do arquivo .LUR
    n = recvfrom(sock, &req, sizeof(req), 0,
                 (struct sockaddr *)&client_addr, &addr_len);
    if (n < 0)
    {
        ESP_LOGE(TAG, "Erro no recvfrom WRQ: errno=%d", errno);
        return ST_ERROR;
    }
    opcode = ntohs(req.opcode);

    if (opcode == OP_WRQ)
    {
        filename = req.request;
        // CORREÇÃO: Garantir terminação de string
        filename[n - 2] = '\0';
        handle_wrq(sock, &client_addr, filename, &lur_file);

        // Verifica se o PN recebido é suportado pelo módulo B/C
        if (!is_pn_supported(lur_file.load_part_number))
        {
            ESP_LOGE(TAG, "PN não suportado: %s", lur_file.load_part_number);
            return ST_ERROR;
        }

        ESP_LOGI(TAG, "PN %s verificado e suportado", lur_file.load_part_number);

        return ST_UPLOADING; // Transição para uploading
    }
    else
    {
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
