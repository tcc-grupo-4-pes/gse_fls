#include "state_machine/fsm.h"
#include "esp_log.h"
#include "esp_err.h"
#include "wifi.h"
#include "lwip/sockets.h"
#include "lwip/inet.h"
#include <string.h>
#include <errno.h>

static const char *TAG = "STATE_MAINT_WAIT";

static bool maint_wait_initialized = false;

static void state_maint_wait_enter(void)
{
    ESP_LOGI(TAG, "INIT ST_MAINT_WAIT");

    /* BC-LLR-6 Criação do ponto de acesso Wifi
    Ao entrar no estado MAINT_WAIT, o módulo B/C deve inicializar o Wi-Fi em modo Access Point, 
    configurado para operar no canal fixo 1 , somente se ele não tiver sido criado antes */
    if (!maint_wait_initialized)
    {
        /* BC-LLR -6 - 7 - 8 
        Criação do ponto de acesso Wifi,
        Configurações do WI-FI
        Configuração IP do WI-Fi AP */
        ESP_LOGI(TAG, "WIFI softAP iniciando...");
        wifi_init_softap();
        ESP_LOGI(TAG, "WIFI softAP iniciado com sucesso");

        sock = socket(AF_INET, SOCK_DGRAM, 0);
        /* BC-LLR-13 - Erro ao criar socket
        No estado MAINT_WAIT caso haja erro ao criar o sock, 
        o software do B/C deve ir para o estado de ERROR e parar a execução da tarefa
        */
        if (sock < 0) /* retorna > 0 se sucesso (numero arbitrario do sistema)
                          retorno < 0  se erro*/
        {
            ESP_LOGE(TAG, "Erro ao criar socket: errno=%d", errno);
            return;
        }

        /* Configura um timeout (tempo máximo de espera)
        para operações de recepção no socket.
        5 segundos eh o padrao RFC 1350, vamos usar 2 segundos */
        struct timeval tv;            /* Estrutura para definir o timeout */
        tv.tv_sec = 2;                /* BC-LLR-16 Tempo de espera em segundos - 2 segundos */
        tv.tv_usec = 0;               /* BC-LLR-16 Tempo de espera em microsegundos - 0 microsegundos */

        /* BC-LLR-16 */
        setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

        /* BC-LLR-9 - Abertura do Socket 
        O software do B/C, no estado MAINT_WAIT após conexão estabelecida com GSE, 
        deve abrir um socket UDP para comunicação usando o protocolo ARINC615A(implementado via TFTP) na porta 69 
        para aceitar requisições de transferência
        */
        memset(&server_addr, 0, sizeof(server_addr));    /* zera todos os bits da estrutura */
        server_addr.sin_family = AF_INET;                /* Família de endereços IPv4 */
        server_addr.sin_port = htons(TFTP_PORT);         /* BC-LLR-90 Porta 69 do TFTP - htons converte de host byte order para network byte order */
        server_addr.sin_addr.s_addr = htonl(INADDR_ANY); /* Endereço IP do servidor - htonl converte de host byte order para network byte order,
            INADDR_ANY significa que o servidor irá escutar em todas as interfaces de rede disponíveis */

        /* BC-LLR-14 - Erro no bind da porta 69 
        No estado MAINT_WAIT caso haja falha no bind inicial, 
        o software do B/C deve ir para o estado de ERROR e parar a execução da tarefa
        */
        if (bind(sock, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) /* Associa o socket ao endereço e porta especificados */
        {
            ESP_LOGE(TAG, "Erro no bind: errno=%d", errno);
            close(sock); /* fecha o socket */
            return;
        }

        addr_len = sizeof(client_addr);
        ESP_LOGI(TAG, "Servidor TFTP rodando na porta %d", TFTP_PORT);

        maint_wait_initialized = true;
    }
    else
    {
        ESP_LOGI(TAG, "Sistema já inicializado, pulando configuração WiFi/socket");
    }

    /* Carrega chaves de autenticação
    Implementa BC-LLR-80, BC-LLR-81 , BC-LLR-82 , BC-LLR-83, BC-LLR-84
    */
    if (auth_load_keys(&auth_keys) != ESP_OK)
    {
        ESP_LOGE(TAG, "Falha ao carregar chaves de autenticação");
        return;
    }


    while (1)
    {   
        /* BC-LLR-10 Autenticação de Aplicação Embraer - GSE
        O software do B/C, no estado MAINT_WAIT após abertura do socket, 
        deve receber uma chave de autenticação do GSE 
        e compara com a chave de autenticação embarcada para autenticar GSE como aplicação Embraer

        BC-LLR-11 Autenticação de Aplicação Embraer - B/C
        O software do B/C, no estado MAINT_WAIT após validação da chave do GSE, 
        deve enviar outra chave atestando aplicação Embraer para o GSE completando o handshake de autenticação
        */
        esp_err_t handshake_result = auth_perform_handshake(sock, &client_addr, &auth_keys);

        if (handshake_result == ESP_OK)
        {
            break;
        }
        else if (handshake_result == ESP_ERR_TIMEOUT)
        {
            continue;
        }
        else
        {
            ESP_LOGW(TAG, "Erro no handshake (%d), aguardando nova tentativa...", handshake_result);
        }
    }

    ESP_LOGI(TAG, "Handshake de autenticação concluído com sucesso");
    auth_clear_keys(&auth_keys); /* BC-LLR-20 Limpeza do buffer da chave pré-compartilhada */
}

static fsm_state_t state_maint_wait_run(void)
{
    if (sock < 0)
    {
        ESP_LOGE(TAG, "Socket não inicializado");
        return ST_ERROR;
    }

    
    n = recvfrom(sock, &req, sizeof(req), 0,
                 (struct sockaddr *)&client_addr, &addr_len);

    /* BC-LLR-85 - Tratamento de Erros na Recepção de Pacotes
    No estado MAINT_WAIT, caso ocorra erro na recepção de pacotes UDP (recvfrom retorna < 0),
    o B/C deve diferenciar entre timeout esperado (errno EAGAIN ou EWOULDBLOCK) e erros críticos.
    Para timeout, o sistema deve permanecer no estado MAINT_WAIT aguardando nova tentativa.
    Para outros erros, deve registrar o erro e permanecer no estado MAINT_WAIT para recuperação.
    */
    if (n < 0) /* tratamento de erro */
    {
        // CORREÇÃO: Timeout é esperado, não é erro crítico
        if (errno == EAGAIN || errno == EWOULDBLOCK)
        {
            // Timeout normal, continua loop
            return ST_MAINT_WAIT;
        }
        ESP_LOGE(TAG, "Erro no recvfrom: errno=%d", errno);
        return ST_MAINT_WAIT;
    }

    /* BC-LLR-15  Erro de pacotes muito pequenos
    No estado MAINT_WAIT caso pacotes recebidos sejam menores que 4 bytes(mínimo), 
    o software deve desconsiderar e esperar novo pacote*/
    if (n < 4) /* tratamento de erro - pacote mínimo nao atingido */
    {
        ESP_LOGW(TAG, "Pacote muito pequeno recebido (%d bytes)", (int)n);
        upload_failure_count++;
        return ST_MAINT_WAIT;
    }

    /* BC-LLR-89 Conversão do OPCODE - Recebimento
    Ao receber um pacote via TFTP, o software do B/C deve converter o OPCODE do 
    formato rede (big-endian) para formato host (little-endian do ESP32).
    */
    opcode = ntohs(req.opcode); 

    /* BC-LLR-12 - Habilitação da interface de carregamento 
    O software do B/C, no estado MAINT_WAIT após autenticação de aplicação Embraer, deve esperar
    a requisição de leitura(Read Request - RRQ) do arquivo Load Upload Initialization(LUI) para
    iniciar a sequência de recebimento do novo firmware(ir para o estado UPLOAD_PREP).
    */
    if (opcode == OP_RRQ)
    {
        filename = req.request;
        filename[n - 2] = '\0';

        /* BC-LLR-23 Porta Efêmera para transferência
        O software do módulo B/C deve se comunicar através de uma porta efêmera para transferir 
        dados conforme descrito no TFTP 
        */
        struct sockaddr_in original_client_addr = client_addr;

        /* BC-LLR-24 Criação do arquivo .LUI
        No estado MAINT_WAIT, após receber a requisição de leitura do arquivo de inicialização deve criar
        e enviar por um buffer o Load Upload Initialization(LUI) aceitando a operação caso não haja nenhum
        problema
        */
        handle_rrq(sock, &client_addr, filename);

        // Restaura endereço original do cliente para make_wrq
        client_addr = original_client_addr;

        return ST_UPLOAD_PREP; // Transição para o Read request primeiro
    }
    /* BC-LLR-18 Opcode desconhecido TFTP
    Caso o OPCODE do pacote recebido via TFTP não seja reconhecido(RRQ,WRQ,DATA,ACK,ERROR),
    o software deve desconsiderar e esperar novo pacote */
    else
    {
        ESP_LOGW(TAG, "Opcode desconhecido recebido: %d", opcode);
        upload_failure_count++;
        return ST_MAINT_WAIT;
    }
}

static void state_maint_wait_exit(void)
{
    ESP_LOGI(TAG, "EXIT ST_MAINT_WAIT");
}

const state_ops_t state_maint_wait_ops = {
    .enter = state_maint_wait_enter,
    .run = state_maint_wait_run,
    .exit = state_maint_wait_exit,
    .name = "ST_MAINT_WAIT"};
