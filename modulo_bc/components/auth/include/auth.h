#ifndef AUTH_H
#define AUTH_H

#include "esp_err.h"
#include <stdint.h>
#include <stdbool.h>
#include <sys/socket.h>
#include <netinet/in.h>

#define KEYS_MOUNT_POINT "/keys"
#define BC_KEY_SIZE 32
#define GSE_KEY_SIZE 32

#define BC_KEY_FILE "/keys/bc_key.bin"
#define GSE_KEY_FILE "/keys/gse_key.bin"

// Estrutura para armazenar chaves na memória
typedef struct
{
    uint8_t bc_auth_key[BC_KEY_SIZE];     // Chave que BC envia para GSE
    uint8_t gse_verify_key[GSE_KEY_SIZE]; // Chave esperada do GSE
} auth_keys_t;

// Função para escrever chaves estáticas na partição (apenas INIT)
esp_err_t auth_write_static_keys(void);

// Função para carregar chaves da partição para memória (MAINT_WAIT)
esp_err_t auth_load_keys(auth_keys_t *keys);

// Função para limpar buffers de chaves da memória
void auth_clear_keys(auth_keys_t *keys);

// Função para handshake de autenticação via TFTP
esp_err_t auth_perform_handshake(int sock, struct sockaddr_in *client_addr, auth_keys_t *keys);

// Função para verificar se já foi autenticado
bool auth_is_authenticated(void);

// Função para resetar estado de autenticação
void auth_reset_authentication(void);

#endif // AUTH_H