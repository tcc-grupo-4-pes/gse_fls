/**
 * @file auth.h
 * @brief Sistema de autenticação mútua entre GSE e módulo B/C
 *
 * Este arquivo define as estruturas e funções para o processo de autenticação
 * baseado em chaves pré-compartilhadas entre o GSE (Ground Support Equipment)
 * e o módulo B/C. A autenticação é realizada através de um handshake mútuo
 * onde ambas as partes validam suas identidades antes de iniciar transferência
 * de firmware.
 *
 * O processo de autenticação ocorre no estado MAINT_WAIT e envolve:
 * 1. GSE envia sua chave de autenticação para o B/C
 * 2. B/C valida a chave recebida contra chave esperada armazenada
 * 3. B/C envia sua própria chave de autenticação para o GSE
 * 4. GSE confirma recebimento e validação da chave do B/C
 *
 * @note Requisitos implementados: BC-LLR-10, BC-LLR-11, BC-LLR-18, BC-LLR-19,
 * BC-LLR-20, BC-LLR-50, BC-LLR-80, BC-LLR-81, BC-LLR-82, BC-LLR-83, BC-LLR-84,
 * BC-LLR-85, BC-LLR-91, BC-LLR-92, BC-LLR-93
 */

#ifndef AUTH_H
#define AUTH_H

#include "esp_err.h"
#include <stdint.h>
#include <stdbool.h>
#include <sys/socket.h>
#include <netinet/in.h>

/**
 * @brief Ponto de montagem da partição de chaves
 * @note BC-LLR-50: Chaves devem ser armazenadas em partição dedicada
 */
#define KEYS_MOUNT_POINT "/keys"

/** @brief Tamanho da chave de autenticação do B/C em bytes */
#define BC_KEY_SIZE 32

/** @brief Tamanho da chave de verificação do GSE em bytes */
#define GSE_KEY_SIZE 32

/**
 * @brief Caminho do arquivo contendo chave do B/C
 * @note BC-LLR-50: Arquivo armazenado na partição /keys
 */
#define BC_KEY_FILE "/keys/bc_key.bin"

/**
 * @brief Caminho do arquivo contendo chave esperada do GSE
 * @note BC-LLR-50: Arquivo armazenado na partição /keys
 */
#define GSE_KEY_FILE "/keys/gse_key.bin"

/**
 * @brief Estrutura para armazenar chaves de autenticação na memória
 *
 * Contém as duas chaves necessárias para o processo de autenticação mútua:
 * - Chave que o B/C envia ao GSE para se autenticar
 * - Chave esperada do GSE para validar sua autenticidade
 */
typedef struct
{
    uint8_t bc_auth_key[BC_KEY_SIZE];     /**< Chave que B/C envia para GSE se autenticar */
    uint8_t gse_verify_key[GSE_KEY_SIZE]; /**< Chave esperada do GSE para validação */
} auth_keys_t;

/**
 * @brief Escreve chaves estáticas na partição de chaves
 *
 * Grava as chaves pré-definidas (hardcoded) nos arquivos da partição SPIFFS.
 * Esta função deve ser chamada apenas no estado INIT para inicializar as chaves
 * quando ainda não existem na partição.
 *
 * @return ESP_OK em sucesso, ESP_FAIL se houver erro ao criar ou escrever arquivos
 * @note Deve ser executada apenas no estado INIT
 */
esp_err_t auth_write_static_keys(void);

/**
 * @brief Carrega chaves da partição SPIFFS para memória RAM
 *
 * Lê os arquivos de chaves da partição e carrega seus conteúdos para a estrutura
 * fornecida. Esta função é chamada no estado MAINT_WAIT antes de iniciar o processo
 * de autenticação. Valida se exatamente 32 bytes são lidos de cada arquivo.
 *
 * @param[out] keys Ponteiro para estrutura onde chaves serão armazenadas
 * @return ESP_OK em sucesso
 * @return ESP_ERR_INVALID_ARG se ponteiro for NULL
 * @return ESP_FAIL se houver erro ao abrir ou ler arquivos
 *
 * @note Requisitos presentes: BC-LLR-80, BC-LLR-81, BC-LLR-82, BC-LLR-83,BC-LLR-84
 */
esp_err_t auth_load_keys(auth_keys_t *keys);

/**
 * @brief Limpa buffers de chaves da memória por segurança
 *
 * Zera todos os bytes das chaves armazenadas na estrutura para evitar que
 * permaneçam em memória após uso. Deve ser chamada após conclusão da autenticação.
 *
 * @param[in,out] keys Ponteiro para estrutura de chaves a ser limpa
 *
 * @note Requisitos presentes: BC-LLR-20
 */
void auth_clear_keys(auth_keys_t *keys);

/**
 * @brief Executa handshake de autenticação mútua com o GSE via TFTP
 *
 * Implementa o protocolo completo de autenticação:
 * 1. Recebe chave do GSE e valida contra chave esperada
 * 2. Envia ACK confirmando recebimento
 * 3. Envia chave do B/C para o GSE
 * 4. Aguarda ACK do GSE confirmando validação
 *
 * A função bloqueia até completar o handshake ou ocorrer erro/timeout.
 * Em caso de sucesso, marca o sistema como autenticado.
 *
 * @param[in] sock Socket UDP configurado para comunicação TFTP
 * @param[in,out] client_addr Estrutura de endereço do cliente GSE
 * @param[in] keys Estrutura contendo chaves carregadas para autenticação
 * @return ESP_OK se autenticação bem-sucedida
 * @return ESP_ERR_TIMEOUT se timeout na recepção
 * @return ESP_FAIL se erro de rede, validação de chave falhar ou formato incorreto
 *
 * @note Requisitos presentes: BC-LLR-10, BC-LLR-11, BC-LLR-18, BC-LLR-19, BC-LLR-27, BC-LLR-28, BC-LLR-85, BC-LLR-89, BC-LLR-90,
 * BC-LLR-91, BC-LLR-92, BC-LLR-93
 */
esp_err_t auth_perform_handshake(int sock, struct sockaddr_in *client_addr, auth_keys_t *keys);

/**
 * @brief Verifica se o sistema já foi autenticado
 *
 * Consulta flag interna que indica se o handshake de autenticação foi
 * concluído com sucesso nesta sessão.
 *
 * @return true se autenticado, false caso contrário
 */
bool auth_is_authenticated(void);

/**
 * @brief Reseta o estado de autenticação
 *
 * Limpa a flag de autenticação, forçando novo handshake na próxima
 * tentativa de comunicação. Usado tipicamente em transições de estado
 * ou após erros.
 */
void auth_reset_authentication(void);

/**
 * @brief Define estado de autenticação (apenas para testes)
 *
 * Permite simular estado autenticado/não-autenticado em ambiente de teste
 * sem executar o handshake real.
 *
 * @param[in] value true para marcar como autenticado, false caso contrário
 * @warning Esta função existe apenas para testes unitários
 */
void auth_set_authenticated_for_test(bool value);

#endif // AUTH_H