#ifndef WIFI_H
#define WIFI_H

#include <string.h>
#include <arpa/inet.h>

#include "esp_netif.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "nvs_flash.h"

#define WIFI_SSID "ESP32_TFTP"
#define WIFI_PASS "12345678"
#define AP_IP "192.168.4.1"
#define AP_NETMASK "255.255.255.0"

void wifi_init_softap(void);

#endif // WIFI_H
