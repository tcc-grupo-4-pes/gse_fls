/**
 * @file wifi.h
 * @brief Componente de inicialização e configuração do Wi-Fi em modo Access Point
 *
 * Este módulo fornece funções para configurar o ESP32 como ponto de acesso Wi-Fi (SoftAP)
 * com configurações específicas do sistema B/C. Inclui configuração de SSID, senha,
 * canal fixo, IP estático e servidor DHCP.
 *
 * @note BC-LLR-6, BC-LLR-7, BC-LLR-8
 */

#ifndef WIFI_H
#define WIFI_H

#include "esp_netif.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "nvs_flash.h"

#define WIFI_SSID "FCC01"          /**< SSID do Access Point (BC-LLR-7) */
#define WIFI_PASS "embraerBC"      /**< Senha WPA/WPA2-PSK do AP (BC-LLR-7) */
#define AP_IP "192.168.4.1"        /**< Endereço IP estático do AP (BC-LLR-8) */
#define AP_NETMASK "255.255.255.0" /**< Máscara de sub-rede do AP (BC-LLR-8) */

/**
 * @brief Inicializa o Wi-Fi em modo Access Point (SoftAP)
 *
 * Configura o ESP32 como ponto de acesso Wi-Fi com:
 * - SSID visível (FCC01)
 * - Autenticação WPA/WPA2-PSK com senha conhecida
 * - Canal fixo 1
 * - Máximo de 1 conexão simultânea
 * - IP estático 192.168.4.1 com máscara 255.255.255.0
 * - Servidor DHCP para clientes
 *
 * Esta função é idempotente: se o AP já foi inicializado, não tenta reconfigurar.
 *
 * @note BC-LLR-6, BC-LLR-7, BC-LLR-8
 */
void wifi_init_softap(void);

#endif // WIFI_H
