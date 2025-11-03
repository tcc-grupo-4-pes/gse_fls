#ifndef WIFI_H
#define WIFI_H

#include "esp_netif.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "nvs_flash.h"

#define WIFI_SSID "FCC01"
#define WIFI_PASS "embraerBC"
#define AP_IP "192.168.4.1"
#define AP_NETMASK "255.255.255.0"

void wifi_init_softap(void);

#endif // WIFI_H
