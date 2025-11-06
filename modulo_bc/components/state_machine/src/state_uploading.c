#include "state_machine/fsm.h"
#include "esp_log.h"
#include "lwip/inet.h"
#include <errno.h>

static const char *TAG = "STATE_UPLOADING";

static struct sockaddr_in original_client_addr;

static void state_uploading_enter(void)
{
    ESP_LOGI(TAG, "INIT ST_UPLOADING");

    /* BC-LLR-101 Preservação do endereço do cliente
       No estado UPLOADING, antes de iniciar a transferência do firmware, 
       o software deve salvar o endereço original do cliente (GSE) para restauração 
       posterior ao envio do LUS
    */
    original_client_addr = client_addr;

    make_rrq(sock, &client_addr, lur_file.header_filename, hash);
}

static fsm_state_t state_uploading_run(void)
{
    ESP_LOGI(TAG, "RUNNING ST_UPLOADING");

    /* BC-LLR-40 Pacote SHA256 esperado
       No estado UPLOADING, após receber todos os pacotes do firmware, 
       o software do B/C deve esperar um último pacote com o SHA256 para verificação de integridade
    */    
    if (recvfrom(sock, &req, sizeof(req), 0,
                 (struct sockaddr *)&client_addr, &addr_len) < 0)
    {   
        /* BC-LLR-63 Erro de não recebimento do SHA256 ao final
        No estado UPLOADING, caso o SHA256 esperado (enviado pelo GSE) não seja recebido, 
        o software do B/C deve ir para o estado ERROR e parar a execução da tarefa
        */
        ESP_LOGE(TAG, "Erro no recvfrom do hash: errno=%d", errno);
        return ST_ERROR;
    }

    // Envia ACK para o hash recebido
    tftp_packet_t hash_ack;
    hash_ack.opcode = htons(OP_ACK);/*BC-LLR-90*/
    hash_ack.block = req.data.block; // Mantém o mesmo número do bloco recebido
    
    /* BC-LLR-64 Erro ao enviar ACK do hash esperado
       No estado UPLOADING, caso haja erro ao enviar o ACK referente ao hash recebido, 
       o software deve ir para o estado ERROR e parar a execução
    */
    if (sendto(sock, &hash_ack, 4, 0,
               (struct sockaddr *)&client_addr, addr_len) < 0)/*BC-LLR-28*/
    {
        ESP_LOGE(TAG, "Erro ao enviar ACK do hash: errno=%d", errno);
        return ST_ERROR;
    }
    ESP_LOGI(TAG, "ACK enviado para hash (bloco %d)", ntohs(req.data.block));

    /* BC-LLR-102 Restauração do endereço do cliente
       No estado UPLOADING, após receber o hash esperado, o software deve restaurar 
       o endereço original do cliente (GSE) para que o LUS seja enviado para a porta 
       principal (69) e não para o TID efêmero
    */
    client_addr = original_client_addr;
    ESP_LOGI(TAG, "Endereço do cliente restaurado para IP=%s, porta=%d",
             inet_ntoa(client_addr.sin_addr), ntohs(client_addr.sin_port)); 

    /* BC-LLR-41 Transição para estado VERIFY
       No estado UPLOADING, após receber o pacote contendo o SHA256 esperado, 
       o software do B/C deve transicionar para o estado VERIFY
    */
    return ST_VERIFY;
}

static void state_uploading_exit(void)
{
    ESP_LOGI(TAG, "EXIT ST_UPLOADING");
}

const state_ops_t state_uploading_ops = {
    .enter = state_uploading_enter,
    .run = state_uploading_run,
    .exit = state_uploading_exit,
    .name = "ST_UPLOADING"};
