#include "wifi.h"
#include <arpa/inet.h>

static const char *TAG = "wifi_component";

void wifi_init_softap(void)
{
    static bool ap_started = false;

    /* Se já inicializamos o AP anteriormente, não tentamos reconfigurar/reiniciar.
       Isso evita desconexões/reconfigurações desnecessárias quando voltamos ao estado MAINT_WAIT. */
    if (ap_started)
    {
        ESP_LOGI(TAG, "API já inicializada, pulando inicialização do softAP");
        return;
    }

    /*
    BC-LLR-6 - Criação do ponto de acesso Wifi
    Ao entrar no estado MAINT_WAIT, 
    o módulo B/C deve inicializar o Wi-Fi em modo Access Point,
     configurado para operar no canal fixo 1 ,somente se ele não tiver sido criado antes
    */
    esp_err_t ret = esp_netif_init();
    if (ret != ESP_OK && ret != ESP_ERR_INVALID_STATE)
    {
        ESP_ERROR_CHECK(ret);
    }

    /* BC-LLR6*/
    ret = esp_event_loop_create_default();
    if (ret != ESP_OK && ret != ESP_ERR_INVALID_STATE)
    {
        ESP_ERROR_CHECK(ret);
    }

    /*
    BC-LLR-6 - Criação do ponto de acesso Wifi
    Ao entrar no estado MAINT_WAIT, 
    o módulo B/C deve inicializar o Wi-Fi em modo Access Point,
     configurado para operar no canal fixo 1 ,somente se ele não tiver sido criado antes
    */
    esp_netif_t *ap_netif = esp_netif_get_handle_from_ifkey("WIFI_AP_DEF");
    if (ap_netif == NULL) {
        /* Cria netif AP padrão apenas se não existir */
        ap_netif = esp_netif_create_default_wifi_ap();
        if (ap_netif == NULL)
        {
            ESP_LOGE(TAG, "falha ao criar esp_netif AP");
            return;
        }
    }
    else
    {
        ESP_LOGW(TAG, "Interface Wi-Fi AP já existe, reutilizando");
    }

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT(); /* BC-LLR-6 - Configuração inicial do Wi-Fi */
    ret = esp_wifi_init(&cfg);
    if (ret != ESP_OK && ret != ESP_ERR_INVALID_STATE)
    {
        ESP_ERROR_CHECK(ret);
    }
    else if (ret == ESP_ERR_INVALID_STATE)
    {
        ESP_LOGW(TAG, "Wi-Fi já foi inicializado");
    }

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_AP));

    /* BC-LLR-7 - Configurações do WI-FI 
    O AP deve operar com SSID visível (FCC01), 
    utilizar autenticação WPA/WPA2-PSK com senha conhecida pelo operador 
    e suportar um máximo de 1 conexão simultânea.
    */
    wifi_config_t ap_config = {
        .ap = {
            .ssid = WIFI_SSID, /* BC-LLR-7 - SSID visível */
            .ssid_len = 0,
            .channel = 1, /* BC-LLR-6 - Canal fixo 1 */
            .password = WIFI_PASS, /* BC-LLR-7 - Senha do Wi-Fi */
            .max_connection = 1, /* BC-LLR-7 - 1 conexao*/
            .authmode = WIFI_AUTH_WPA_WPA2_PSK, /* BC-LLR-7 - WPA/WPA2-PSK */
            .ssid_hidden = 0}, /* BC-LLR-7 - SSID visível */
    };

    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &ap_config));
    ESP_ERROR_CHECK(esp_wifi_start());

    /* BC-LLR-8 - Configuração IP do AP
    A interface de rede do AP deve ser configurada com um IP estático 
    (conforme IP 192.168.4.1 e NETMASK: 255.255.255.0) 
    e deve prover um servidor DHCP para os clientes conectados.
    */
    esp_netif_ip_info_t ip;
    ip.ip.addr = inet_addr(AP_IP); /* BC-LLR-8 - IP estático */
    ip.netmask.addr = inet_addr(AP_NETMASK); /* BC-LLR-8 - NETMASK estático */
    ip.gw.addr = inet_addr(AP_IP); /* BC-LLR-8 - GATEWAY estático */

    /* BC-LLR-8 - Desliga e reinicia DHCP server, seta IP e liga novamente,
    para aplicar BC-LLR-8 */
    esp_netif_dhcps_stop(ap_netif);
    ret = esp_netif_set_ip_info(ap_netif, &ip);
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

    ap_started = true;
}
