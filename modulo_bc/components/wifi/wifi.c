#include "wifi.h"

static const char *TAG = "wifi_component";


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
