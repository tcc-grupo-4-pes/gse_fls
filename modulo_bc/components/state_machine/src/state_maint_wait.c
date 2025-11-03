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

    /* Se já foi inicializado (retorno do teardown), pula reinicialização do WiFi e socket */
    if (!maint_wait_initialized)
    {
        /* BC-LLR-6 - Criação do ponto de acesso Wifi - Ao entrar no estado MAINT_WAIT,
        o módulo B/C deve inicializar o Wi-Fi
        em modo Access Point, configurado para operar no canal fixo 1 */
        ESP_LOGI(TAG, "WIFI softAP iniciando...");
        wifi_init_softap();
        ESP_LOGI(TAG, "WIFI softAP iniciado com sucesso");

        /* Criação do socket UDP
        AF_INET -> IPv4 exemplo 192.168.1.1
        SOCK_DGRAM -> Tipo de socket para comunicação UDP
        0 -> Protocolo padrão para UDP (IPPROTO_UDP)
        */
        sock = socket(AF_INET, SOCK_DGRAM, 0);
        if (sock < 0) /* retorna > 0 se sucesso (numero arbitrario do sistema)
                          retorno < 0  se erro*/
        {
            ESP_LOGE(TAG, "Erro ao criar socket: errno=%d", errno);
            return;
        }

        /* Configura um timeout (tempo máximo de espera)
        para operações de recepção no socket.
        5 segundos eh o padrao RFC 1350 */
        struct timeval tv;            /* Estrutura para definir o timeout */
        tv.tv_sec = TFTP_TIMEOUT_SEC; /* Tempo de espera em segundos - 5 segundos em tftp.h */
        tv.tv_usec = 0;               /* Tempo de espera em microsegundos - 0 microsegundos */

        setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

        /* Configura endereço do servidor */
        memset(&server_addr, 0, sizeof(server_addr));    /* zera todos os bits da estrutura */
        server_addr.sin_family = AF_INET;                /* Família de endereços IPv4 */
        server_addr.sin_port = htons(TFTP_PORT);         /* Porta do servidor TFTP - htons converte de host byte order para network byte order */
        server_addr.sin_addr.s_addr = htonl(INADDR_ANY); /* Endereço IP do servidor - htonl converte de host byte order para network byte order,
            INADDR_ANY significa que o servidor irá escutar em todas as interfaces de rede disponíveis */

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

    /* Carrega chaves de autenticação (sempre executa, mesmo em reinicializações) */
    if (auth_load_keys(&auth_keys) != ESP_OK)
    {
        ESP_LOGE(TAG, "Falha ao carregar chaves de autenticação");
        return;
    }

    /* Aguarda primeira conexão do GSE para handshake */
    ESP_LOGI(TAG, "Aguardando conexão inicial do GSE para autenticação...");

    /* Realizar handshake de autenticação antes de processar qualquer request */
    ESP_LOGI(TAG, "Iniciando handshake de autenticação...");

    while (1)
    {
        esp_err_t handshake_result = auth_perform_handshake(sock, &client_addr, &auth_keys);

        if (handshake_result == ESP_OK)
        {
            break;
        }

        if (handshake_result == ESP_ERR_TIMEOUT)
        {
            ESP_LOGW(TAG, "Timeout aguardando GSE, tentando novamente...");
            continue;
        }
        else
        {
            ESP_LOGW(TAG, "Erro no handshake (%d), aguardando nova tentativa...", handshake_result);
        }
    }

    ESP_LOGI(TAG, "Handshake de autenticação concluído com sucesso");
    auth_clear_keys(&auth_keys); // Limpa buffers após handshake
}

static fsm_state_t state_maint_wait_run(void)
{
    if (sock < 0)
    {
        ESP_LOGE(TAG, "Socket não inicializado");
        return ST_ERROR;
    }

    /* recvfrom()
        Aguarda receber um pacote UDP e armazena:
        Dados do pacote em req
        Endereço do remetente em client_addr*/
    n = recvfrom(sock, &req, sizeof(req), 0,
                 (struct sockaddr *)&client_addr, &addr_len);

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

    if (n < 4) /* tratamento de erro - pacote mínimo nao atingido */
    {
        ESP_LOGW(TAG, "Pacote muito pequeno recebido (%d bytes)", (int)n);
        upload_failure_count++;
        return ST_MAINT_WAIT;
    }

    /* parse da estrutura recebida via tftp */
    opcode = ntohs(req.opcode); /* extrai e converte o opcode,
                                       Converte número de 16 bits do formato rede (big-endian)
                                       para formato host (little-endian do ESP32).*/

    if (opcode == OP_RRQ)
    {
        filename = req.request;
        // CORREÇÃO: Garantir terminação de string
        filename[n - 2] = '\0';

        // Salva endereço original do cliente antes de handle_rrq pois é criado um TID efêmero
        struct sockaddr_in original_client_addr = client_addr;

        handle_rrq(sock, &client_addr, filename);

        // Restaura endereço original do cliente para make_wrq
        client_addr = original_client_addr;

        return ST_UPLOAD_PREP; // Transição para o Read request primeiro
    }
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
