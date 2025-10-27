#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "esp_netif.h"
#include "lwip/sockets.h"
#include "lwip/inet.h"
#include "mbedtls/sha256.h"
#include "esp_heap_caps.h"

// ============ CONFIGURAÇÕES ============
#define WIFI_SSID "ESP32_TFTP"
#define WIFI_PASS "12345678" // mínimo 8 caracteres para WPA2
#define AP_IP "192.168.4.1"
#define AP_NETMASK "255.255.255.0"
#define TFTP_PORT 69
#define BLOCK_SIZE 512
// ============ CÓDIGOS TFTP ============
#define OP_RRQ 1   // Read request (download)
#define OP_WRQ 2   // Write request (upload)
#define OP_DATA 3  // Pacote de dados
#define OP_ACK 4   // Confirmação
#define OP_ERROR 5 // Erro

#define TFTP_RETRY_LIMIT 5
#define TFTP_TIMEOUT_SEC 5

typedef enum
{
    ARINC_STATUS_OP_ACCEPTED_NOT_STARTED = 0x0001, /**< Operação aceita, mas ainda não iniciada.  */
    ARINC_STATUS_OP_IN_PROGRESS = 0x0002,          /**< Operação em progresso. */
    ARINC_STATUS_OP_COMPLETED_OK = 0x0003,         /**< Operação completada sem erros.  */
    ARINC_STATUS_OP_REJECTED = 0x1000,             /**< Operação não aceita pelo target.  */
    ARINC_STATUS_OP_ABORTED_BY_TARGET = 0x1003,    /**< Operação abortada pelo target hardware.  */
    ARINC_STATUS_OP_ABORTED_BY_LOADER = 0x1004,    /**< Operação abortada pelo data loader.  */
    ARINC_STATUS_OP_CANCELLED_BY_USER = 0x1005,    /**< Operação cancelada pelo operador.  */
} arinc_op_status_code_t;                          // De acordo com tabela slide 38 arinc

static const char *TAG = "B/C";

// ESTRUTURA DO PACOTE TFTP
typedef struct
{
    uint16_t opcode;
    union
    {
        char request[514]; // No formato 'filename\0mode\0' para RRQ/WRQ
        struct
        { // Para DATA
            uint16_t block;
            uint8_t data[512];
        } data;
        uint16_t block; // Para ACK
        struct
        { // Para ERROR
            uint16_t code;
            char msg[512];
        } error;
    };
} __attribute__((packed)) tftp_packet_t; // __attribute__((packed)) para evitar padding do compilador

typedef struct
{
    char header_filename[256];
    char load_part_number[256];
} lur_info_t;

static lur_info_t g_lur_info;

typedef struct
{
    uint32_t file_length;     // 32 bits
    char protocol_version[2]; // 16 bits
    uint16_t status_code;     // 16 bits
    uint8_t desc_length;      // 8 bits
    char description[256];    // String variável
    uint16_t counter;         // 16 bits - Começa em 0x0000
    uint16_t exception_timer; // 16 bits - 0x0000 se não usado
    uint16_t estimated_time;  // 16 bits - 0x0000 se não usado
    char load_list_ratio[3];  // 3 caracteres ASCII "000" a "100"
} __attribute__((packed)) lus_data_t;

// inicia ESP em modo AP com IP estático
void wifi_init_softap(void)
{
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    // Cria netif AP padrão
    esp_netif_t *ap_netif = esp_netif_create_default_wifi_ap();
    if (ap_netif == NULL)
    {
        ESP_LOGE(TAG, "falha ao criar esp_netif AP");
        return;
    }

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_AP));

    wifi_config_t ap_config = {
        .ap = {
            .ssid = WIFI_SSID,
            .ssid_len = 0,
            .channel = 1,
            .password = WIFI_PASS,
            .max_connection = 4,
            .authmode = WIFI_AUTH_WPA_WPA2_PSK,
            .ssid_hidden = 0},
    };

    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &ap_config));
    ESP_ERROR_CHECK(esp_wifi_start());

    // Configura IP estático da interface AP (192.168.4.1)
    esp_netif_ip_info_t ip;
    ip.ip.addr = inet_addr(AP_IP);
    ip.netmask.addr = inet_addr(AP_NETMASK);
    ip.gw.addr = inet_addr(AP_IP);

    // desliga DHCP server, seta IP e liga novamente
    esp_netif_dhcps_stop(ap_netif);
    esp_err_t ret = esp_netif_set_ip_info(ap_netif, &ip);
    if (ret != ESP_OK)
    {
        ESP_LOGW(TAG, "esp_netif_set_ip_info falhou: %d", ret);
    }
    else
    {
        ESP_LOGI(TAG, "AP IP configurado para %s", AP_IP);
    }
    esp_netif_dhcps_start(ap_netif);

    ESP_LOGI(TAG, "WiFi AP iniciado: SSID='%s' PASS='%s'", WIFI_SSID, WIFI_PASS);
}

// --------------- PROCESSA READ REQUEST RRQ ----------------
// Envia o arquivo .LUI solicitado pelo GSE
void handle_rrq(int sock, struct sockaddr_in *client, char *filename)
{
    ESP_LOGI(TAG, "Read Request(GSE requisita): %s", filename);

    if (strstr(filename, ".LUI") == NULL)
    {
        ESP_LOGW(TAG, "Arquivo requisitado não é .LUI");
        return;
    }

    const char *status_text = "Operation Accepted";
    uint16_t status_be = htons(ARINC_STATUS_OP_ACCEPTED_NOT_STARTED);
    size_t text_len = strlen(status_text) + 1;
    size_t total_size = sizeof(status_be) + text_len;

    uint8_t *lui_buf = malloc(total_size);
    if (lui_buf == NULL)
    {
        ESP_LOGE(TAG, "Falha ao alocar memória para LUI");
        return;
    }

    memcpy(lui_buf, &status_be, sizeof(status_be));
    memcpy(lui_buf + sizeof(status_be), status_text, text_len);

    int sent = 0;
    uint16_t block = 1;
    int retry_count = 0;

    while (sent < total_size)
    {
        tftp_packet_t pkt;
        pkt.opcode = htons(OP_DATA);
        pkt.data.block = htons(block);

        int chunk = (total_size - sent) < BLOCK_SIZE ? (total_size - sent) : BLOCK_SIZE;
        memcpy(pkt.data.data, (uint8_t *)lui_buf + sent, chunk);

        // CORREÇÃO: Usar sendto() para UDP
        ssize_t s = sendto(sock, &pkt, 4 + chunk, 0,
                           (struct sockaddr *)client, sizeof(*client));
        if (s < 0)
        {
            ESP_LOGW(TAG, "Falha ao enviar bloco %d, tentando novamente", block);
            retry_count++;
            if (retry_count >= TFTP_RETRY_LIMIT)
            {
                ESP_LOGE(TAG, "Limite de tentativas atingido para bloco %d", block);
                break;
            }
            vTaskDelay(pdMS_TO_TICKS(TFTP_TIMEOUT_SEC * 1000));
            continue;
        }
        ESP_LOGI(TAG, "Enviado bloco %d (%d bytes)", block, chunk);
        retry_count = 0;

        // CORREÇÃO: Timeout em recv para evitar travamento
        struct timeval tv;
        tv.tv_sec = TFTP_TIMEOUT_SEC;
        tv.tv_usec = 0;
        setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

        // Aguarda ACK
        tftp_packet_t ack;
        struct sockaddr_in ack_addr;
        socklen_t ack_len = sizeof(ack_addr);

        ssize_t n = recvfrom(sock, &ack, sizeof(ack), 0,
                             (struct sockaddr *)&ack_addr, &ack_len);

        if (n > 0 && ntohs(ack.opcode) == OP_ACK && ntohs(ack.block) == block)
        {
            ESP_LOGI(TAG, "ACK recebido para bloco %d", block);
            sent += chunk;
            block++;
        }
        else
        {
            ESP_LOGW(TAG, "ACK não recebido ou inválido, reenviando bloco %d...", block);
        }

        if (chunk < BLOCK_SIZE)
            break;
    }

    free(lui_buf);
    ESP_LOGI(TAG, "RRQ concluido");
}
// --------------- PROCESSA WRITE REQUEST WRQ ----------------
// Recebe o arquivo .LUR enviado pelo GSE
void handle_wrq(int sock, struct sockaddr_in *client, char *filename)
{
    ESP_LOGI(TAG, "Write Request (GSE envia): %s", filename);

    if (strstr(filename, ".LUR") == NULL)
    {
        ESP_LOGW(TAG, "Arquivo recebido não é .LUR");
        return;
    }

    // Confirma recebimento do WRQ (ACK de bloco 0)
    tftp_packet_t ack;
    ack.opcode = htons(OP_ACK);
    ack.block = htons(0);
    sendto(sock, &ack, 4, 0, (struct sockaddr *)client, sizeof(*client));

    // Configura timeout para evitar travamento
    struct timeval tv;
    tv.tv_sec = TFTP_TIMEOUT_SEC;
    tv.tv_usec = 0;
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

    uint16_t expected_block = 1;
    tftp_packet_t pkt;
    struct sockaddr_in recv_addr;
    socklen_t recv_len = sizeof(recv_addr);

    // Buffer temporário em RAM (pequeno arquivo .LUR)
    uint8_t lur_buf[256];
    size_t total_received = 0;

    while (1)
    {
        ssize_t n = recvfrom(sock, &pkt, sizeof(pkt), 0,
                             (struct sockaddr *)&recv_addr, &recv_len);
        if (n < 0)
        {
            ESP_LOGW(TAG, "Timeout ou erro no recebimento (errno=%d)", errno);
            break;
        }

        if (ntohs(pkt.opcode) != OP_DATA || ntohs(pkt.data.block) != expected_block)
        {
            ESP_LOGW(TAG, "Pacote inesperado (opcode=%d, block=%d)",
                     ntohs(pkt.opcode), ntohs(pkt.data.block));
            continue;
        }

        int data_len = n - 4;
        if (total_received + data_len <= sizeof(lur_buf))
        {
            memcpy(lur_buf + total_received, pkt.data.data, data_len);
            total_received += data_len;
        }

        // Envia ACK
        ack.opcode = htons(OP_ACK);
        ack.block = htons(expected_block);
        sendto(sock, &ack, 4, 0, (struct sockaddr *)client, sizeof(*client));

        ESP_LOGI(TAG, "Bloco %d recebido (%d bytes)", expected_block, data_len);
        expected_block++;

        if (data_len < BLOCK_SIZE)
            break; // Último bloco
    }

    if (total_received == 0)
    {
        ESP_LOGW(TAG, "Nenhum dado .LUR recebido");
        return;
    }

    // ====== Parse simplificado do buffer .LUR ======
    uint8_t *p = lur_buf;
    uint32_t file_length = ntohl(*(uint32_t *)p);
    p += 4;
    uint16_t proto_ver = ntohs(*(uint16_t *)p);
    p += 2;
    uint16_t num_headers = ntohs(*(uint16_t *)p);
    p += 2;

    // 1 header file assumido
    uint8_t header_len = *p++;
    memcpy(g_lur_info.header_filename, p, header_len);
    g_lur_info.header_filename[header_len] = '\0';
    p += header_len;

    uint8_t pn_len = *p++;
    memcpy(g_lur_info.load_part_number, p, pn_len);
    g_lur_info.load_part_number[pn_len] = '\0';
    p += pn_len;

    ESP_LOGI(TAG, "LUR recebido e processado da RAM:");
    ESP_LOGI(TAG, "  File length: %lu", file_length);
    ESP_LOGI(TAG, "  Protocol version: %u", proto_ver);
    ESP_LOGI(TAG, "  Header file name: %s", g_lur_info.header_filename);
    ESP_LOGI(TAG, "  Load Part Number: %s", g_lur_info.load_part_number);
}

// Para escrita do .LUS no GSE
void make_wrq(int sock, struct sockaddr_in *client_addr, const char *lus_filename, const lus_data_t *lus_data)
{
    ESP_LOGI(TAG, "Iniciando WRQ para envio de %s", lus_filename);

    // Envia WRQ para o cliente
    tftp_packet_t wrq;
    wrq.opcode = htons(OP_WRQ);
    snprintf(wrq.request, sizeof(wrq.request), "%s%coctet%c", lus_filename, 0, 0);

    if (sendto(sock, &wrq, strlen(lus_filename) + 8, 0,
               (struct sockaddr *)client_addr, sizeof(*client_addr)) < 0)
    {
        ESP_LOGE(TAG, "Erro ao enviar WRQ: errno=%d", errno);
        return;
    }

    // Espera ACK do bloco 0
    tftp_packet_t ack;
    struct sockaddr_in ack_addr;
    socklen_t ack_len = sizeof(ack_addr);

    if (recvfrom(sock, &ack, sizeof(ack), 0,
                 (struct sockaddr *)&ack_addr, &ack_len) < 0)
    {
        ESP_LOGE(TAG, "Erro ao receber ACK inicial: errno=%d", errno);
        return;
    }

    if (ntohs(ack.opcode) != OP_ACK || ntohs(ack.block) != 0)
    {
        ESP_LOGE(TAG, "ACK inicial inválido");
        return;
    }

    // Monta pacote LUS

    // Envia bloco de dados
    tftp_packet_t data_pkt;
    data_pkt.opcode = htons(OP_DATA);
    data_pkt.data.block = htons(1);
    memcpy(data_pkt.data.data, lus_data, sizeof(lus_data_t));

    if (sendto(sock, &data_pkt, 4 + sizeof(lus_data_t), 0,
               (struct sockaddr *)client_addr, sizeof(*client_addr)) < 0)
    {
        ESP_LOGE(TAG, "Erro ao enviar dados LUS: errno=%d", errno);
        return;
    }

    // Espera ACK final
    if (recvfrom(sock, &ack, sizeof(ack), 0,
                 (struct sockaddr *)&ack_addr, &ack_len) < 0)
    {
        ESP_LOGE(TAG, "Erro ao receber ACK final: errno=%d", errno);
        return;
    }

    if (ntohs(ack.opcode) != OP_ACK || ntohs(ack.block) != 1)
    {
        ESP_LOGE(TAG, "ACK final inválido");
        return;
    }

    ESP_LOGI(TAG, "Arquivo LUS enviado com sucesso");
}

void make_rrq(int sock, struct sockaddr_in *client_addr, const char *filename, unsigned char *hash)
{
    ESP_LOGI(TAG, "Iniciando RRQ para %s", filename);

    tftp_packet_t rrq;
    rrq.opcode = htons(OP_RRQ);
    snprintf(rrq.request, sizeof(rrq.request), "%s%coctet%c", filename, 0, 0);

    if (sendto(sock, &rrq, strlen(filename) + 8, 0,
               (struct sockaddr *)client_addr, sizeof(*client_addr)) < 0)
    {
        ESP_LOGE(TAG, "Erro ao enviar RRQ: errno=%d", errno);
        return;
    }

    // Buffer dinâmico para acumular o arquivo recebido
    uint8_t *file_buf = NULL;
    size_t file_cap = 0;
    size_t file_len = 0;

    while (1)
    {
        tftp_packet_t data_pkt;
        struct sockaddr_in data_addr;
        socklen_t addr_len = sizeof(data_addr);

        ssize_t n = recvfrom(sock, &data_pkt, sizeof(data_pkt), 0,
                             (struct sockaddr *)&data_addr, &addr_len);
        if (n < 0)
        {
            ESP_LOGE(TAG, "Erro ao receber dados: errno=%d", errno);
            break;
        }

        if (ntohs(data_pkt.opcode) != OP_DATA)
        {
            ESP_LOGW(TAG, "Pacote inesperado recebido (opcode=%d)", ntohs(data_pkt.opcode));
            continue;
        }

        int data_len = n - 4; // remove opcode(2) + block(2)
        ESP_LOGI(TAG, "Bloco %d recebido (%d bytes)", ntohs(data_pkt.data.block), data_len);

        vTaskDelay(pdMS_TO_TICKS(10));
        // Envia ACK para o bloco recebido
        tftp_packet_t ack;
        ack.opcode = htons(OP_ACK);
        ack.block = data_pkt.data.block; // já em network order

        if (sendto(sock, &ack, 4, 0,
                   (struct sockaddr *)client_addr, sizeof(*client_addr)) < 0)
        {
            ESP_LOGE(TAG, "Erro ao enviar ACK: errno=%d", errno);
            break;
        }

        // Se o bloco foi menor que BLOCK_SIZE, foi o último
        if (data_len < BLOCK_SIZE)
            break;
    }

    if (file_len == 0)
    {
        ESP_LOGW(TAG, "Nenhum dado recebido em make_rrq para %s", filename);
        free(file_buf);
        return;
    }

    // Calcula SHA-256 do arquivo completo
    mbedtls_sha256_context sha256_ctx;
    mbedtls_sha256_init(&sha256_ctx);
    mbedtls_sha256_starts(&sha256_ctx, 0); // 0 para SHA-256
    mbedtls_sha256_update(&sha256_ctx, file_buf, file_len);
    mbedtls_sha256_finish(&sha256_ctx, hash);
    mbedtls_sha256_free(&sha256_ctx);

    ESP_LOGI(TAG, "Arquivo %s recebido com sucesso (%zu bytes)", filename, file_len);
    ESP_LOGI(TAG, "SHA-256: ");
    for (int i = 0; i < 32; i++)
    {
        printf("%02x", hash[i]);
    }
    printf("\n");
    free(file_buf);
}
void main_task(void *pvParameters)
{
    int sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0)
    {
        ESP_LOGE(TAG, "Erro ao criar socket: errno=%d", errno);
        vTaskDelete(NULL);
    }

    // CORREÇÃO: Timeout para recvfrom
    struct timeval tv;
    tv.tv_sec = TFTP_TIMEOUT_SEC;
    tv.tv_usec = 0;
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(TFTP_PORT);
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);

    if (bind(sock, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0)
    {
        ESP_LOGE(TAG, "Erro no bind: errno=%d", errno);
        close(sock);
        vTaskDelete(NULL);
    }

    ESP_LOGI(TAG, "Servidor TFTP rodando na porta %d", TFTP_PORT);

    while (1)
    {
        struct sockaddr_in client_addr;
        socklen_t addr_len = sizeof(client_addr);
        tftp_packet_t req;

        ssize_t n = recvfrom(sock, &req, sizeof(req), 0,
                             (struct sockaddr *)&client_addr, &addr_len);

        if (n < 0)
        {
            // CORREÇÃO: Timeout é esperado, não é erro crítico
            if (errno == EAGAIN || errno == EWOULDBLOCK)
            {
                // Timeout normal, continua loop
                continue;
            }
            ESP_LOGE(TAG, "Erro no recvfrom: errno=%d", errno);
            continue;
        }

        // CORREÇÃO: Validar tamanho mínimo do pacote
        if (n < 4)
        {
            ESP_LOGW(TAG, "Pacote muito pequeno recebido (%d bytes)", (int)n);
            continue;
        }

        uint16_t opcode = ntohs(req.opcode);
        if (opcode == OP_RRQ)
        {
            char *filename = req.request;
            // CORREÇÃO: Garantir terminação de string
            filename[n - 2] = '\0';
            handle_rrq(sock, &client_addr, filename);
        }
        else
        {
            ESP_LOGW(TAG, "Opcode desconhecido recebido: %d", opcode);
        }

        vTaskDelay(pdMS_TO_TICKS(100));

        lus_data_t lus_data;
        memset(&lus_data, 0, sizeof(lus_data)); // Zera toda a estrutura

        const char *status_desc = "Operation Accepted";
        size_t desc_len = strlen(status_desc);

        // Preenche dados do INIT_LOAD.LUS
        lus_data.file_length = htonl(sizeof(lus_data));
        memcpy(lus_data.protocol_version, "A4", 2); // protocol version: "A4"
        lus_data.status_code = htons(ARINC_STATUS_OP_ACCEPTED_NOT_STARTED);
        lus_data.desc_length = desc_len;
        memcpy(lus_data.description, status_desc, desc_len);
        lus_data.counter = htons(0);                // Começa em 0
        lus_data.exception_timer = htons(0);        // Não usado neste momento
        lus_data.estimated_time = htons(0);         // Não usado neste momento
        memcpy(lus_data.load_list_ratio, "000", 3); // 0% completo

        make_wrq(sock, &client_addr, "INIT_LOAD.LUS", &lus_data);

        // Aguarda um write request do GSE para escrita do arquivo .LUR
        n = recvfrom(sock, &req, sizeof(req), 0,
                     (struct sockaddr *)&client_addr, &addr_len);
        if (n < 0)
        {
            ESP_LOGE(TAG, "Erro no recvfrom WRQ: errno=%d", errno);
            continue;
        }
        opcode = ntohs(req.opcode);
        if (opcode == OP_WRQ)
        {
            char *filename = req.request;
            // CORREÇÃO: Garantir terminação de string
            filename[n - 2] = '\0';
            handle_wrq(sock, &client_addr, filename);
        }
        else
        {
            ESP_LOGW(TAG, "Opcode desconhecido recebido: %d", opcode);
            continue;
        }
        // Faz um RRQ para obter o arquivo com o nome obtido do LUR
        unsigned char hash[32]; // SHA-256
        make_rrq(sock, &client_addr, g_lur_info.header_filename, hash);

        // Receber o hash com tftp e comparar com o calculado
        if (recvfrom(sock, &req, sizeof(req), 0,
                     (struct sockaddr *)&client_addr, &addr_len) < 0)
        {
            ESP_LOGE(TAG, "Erro no recvfrom do hash: errno=%d", errno);
            continue;
        }

        // Envia ACK para o hash recebido
        tftp_packet_t hash_ack;
        hash_ack.opcode = htons(OP_ACK);
        hash_ack.block = req.data.block; // Mantém o mesmo número do bloco recebido
        if (sendto(sock, &hash_ack, 4, 0,
                   (struct sockaddr *)&client_addr, addr_len) < 0)
        {
            ESP_LOGE(TAG, "Erro ao enviar ACK do hash: errno=%d", errno);
            continue;
        }
        ESP_LOGI(TAG, "ACK enviado para hash (bloco %d)", ntohs(req.data.block));

        if (memcmp(req.data.data, hash, 32) != 0)
        {
            ESP_LOGE(TAG, "Hash SHA-256 não confere! Arquivo corrompido.");
        }
        else
        {
            ESP_LOGI(TAG, "Hash SHA-256 conferido com sucesso.");
            // Envio do LUS intermediário
            lus_data_t intermediate_lus_data;
            memset(&intermediate_lus_data, 0, sizeof(intermediate_lus_data)); // Zera toda a estrutura
            const char *intermediate_status_desc = "Intermediate Load Accepted";
            size_t intermediate_desc_len = strlen(intermediate_status_desc);
            // Preenche dados do INTERMEDIATE_LOAD.LUS
            intermediate_lus_data.file_length = htonl(sizeof(intermediate_lus_data));
            memcpy(intermediate_lus_data.protocol_version, "A4", 2); // protocol
            intermediate_lus_data.status_code = htons(ARINC_STATUS_OP_IN_PROGRESS);
            intermediate_lus_data.desc_length = intermediate_desc_len;
            memcpy(intermediate_lus_data.description, intermediate_status_desc, intermediate_desc_len);
            intermediate_lus_data.counter = htons(1);                // Incrementa contador
            intermediate_lus_data.exception_timer = htons(0);        // Não usado neste momento
            intermediate_lus_data.estimated_time = htons(0);         // Não usado neste momento
            memcpy(intermediate_lus_data.load_list_ratio, "050", 3); // 50% completo

            make_wrq(sock, &client_addr, "INTERMEDIATE_LOAD.LUS", &intermediate_lus_data);

            // armazena arquivo na partição SPIFFS
            
            // Envio do LUS final
            lus_data_t final_lus_data;
            memset(&final_lus_data, 0, sizeof(final_lus_data)); // Zera toda a estrutura
            const char *final_status_desc = "Load Completed Successfully";
            size_t final_desc_len = strlen(final_status_desc);
            // Preenche dados do FINAL_LOAD.LUS
            final_lus_data.file_length = htonl(sizeof(final_lus_data));
            memcpy(final_lus_data.protocol_version, "A4", 2); // protocol
            final_lus_data.status_code = htons(ARINC_STATUS_OP_COMPLETED_OK);
            final_lus_data.desc_length = final_desc_len;
            memcpy(final_lus_data.description, final_status_desc, final_desc_len);
            final_lus_data.counter = htons(2);                // Incrementa contador
            final_lus_data.exception_timer = htons(0);        // Não usado neste momento
            final_lus_data.estimated_time = htons(0);         // Não usado neste momento
            memcpy(final_lus_data.load_list_ratio, "100", 3); // 100% completo
            make_wrq(sock, &client_addr, "FINAL_LOAD.LUS", &final_lus_data);
        }
    }

    close(sock);
    vTaskDelete(NULL);
}

void app_main(void)
{
    ESP_LOGI(TAG, "Iniciando ESP32");
    

    nvs_flash_init();
    wifi_init_softap();

    xTaskCreate(main_task, "main", 16384, NULL, 5, NULL);
}