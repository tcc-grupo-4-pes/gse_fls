/**
 * @file arinc.h
 * @brief Definições de estruturas e funções do protocolo ARINC 615A
 *
 * Este arquivo define os tipos de dados e funções para manipulação de arquivos
 * do protocolo ARINC 615A utilizados na comunicação entre o GSE (Ground Support Equipment)
 * e o módulo B/C para carregamento de firmware.
 *
 * Inclui definições para:
 * - Códigos de status de operação (LUI/LUS)
 * - Estrutura de arquivo LUI (Load Upload Information)
 * - Estrutura de arquivo LUS (Load Upload Status)
 * - Estrutura de arquivo LUR (Load Upload Request)
 *
 * @note Requisitos implementados: BC-LLR-25, BC-LLR-26, BC-LLR-31, BC-LLR-33
 */

#ifndef ARINC_H
#define ARINC_H

#include <stdint.h>
#include <stddef.h>

/**
 * @brief Códigos de status de operação do protocolo ARINC 615A
 *
 * @note BC-LLR-25: O software do módulo B/C deve usar os códigos de status
 * definidos no Protocolo ARINC615A (conforme tabela do slide 38 do treinamento)
 */
typedef enum
{
    ARINC_STATUS_OP_ACCEPTED_NOT_STARTED = 0x0001, /**< Operação aceita, mas ainda não iniciada. */
    ARINC_STATUS_OP_IN_PROGRESS = 0x0002,          /**< Operação em progresso. */
    ARINC_STATUS_OP_COMPLETED_OK = 0x0003,         /**< Operação completada sem erros. */
    ARINC_STATUS_OP_REJECTED = 0x1000,             /**< Operação não aceita pelo target. */
    ARINC_STATUS_OP_ABORTED_BY_TARGET = 0x1003,    /**< Operação abortada pelo target hardware. */
    ARINC_STATUS_OP_ABORTED_BY_LOADER = 0x1004,    /**< Operação abortada pelo data loader. */
    ARINC_STATUS_OP_CANCELLED_BY_USER = 0x1005,    /**< Operação cancelada pelo operador. */
} arinc_op_status_code_t;

/**
 * @brief Estrutura de arquivo LUI (Load Upload Information)
 *
 * Contém informações iniciais sobre a operação de upload enviadas ao GSE.
 *
 * @note BC-LLR-26: O arquivo .LUI deve conter campos para comprimento do .LUI (32 bits),
 * versão do protocolo (16 bits - "A4"), Status de aceitação da operação (16bits),
 * uma string de descrição do status (até 256 bytes) e o tamanho da string de descrição (8 bits)
 */
typedef struct
{
    uint32_t file_length;     /**< 32 bits - Comprimento total do arquivo LUI */
    char protocol_version[2]; /**< 16 bits - Versão do protocolo (A4) */
    uint16_t status_code;     /**< 16 bits - Código de status ARINC */
    uint8_t desc_length;      /**< 8 bits - Comprimento da descrição */
    char description[256];    /**< String variável - Descrição do status */
} __attribute__((packed)) lui_data_t;

/**
 * @brief Estrutura de arquivo LUS (Load Upload Status)
 *
 * Contém informações de progresso da operação de upload enviadas periodicamente ao GSE.
 *
 * @note BC-LLR-31: O arquivo .LUS deve conter campos para comprimento do .LUS (32 bits),
 * versão do protocolo (16 bits - "A4"), Status de aceitação da operação (16bits),
 * uma string de descrição do status (até 256 bytes) e o tamanho da string de descrição (8 bits),
 * contador (16 bits), exception timer e exception time (16 bits cada),
 * Razão (%) da lista de Load (24 bits - 3 ASCII)
 */
typedef struct
{
    uint32_t file_length;     /**< 32 bits - Comprimento total do arquivo LUS */
    char protocol_version[2]; /**< 16 bits - Versão do protocolo (A4) */
    uint16_t status_code;     /**< 16 bits - Código de status ARINC */
    uint8_t desc_length;      /**< 8 bits - Comprimento da descrição */
    char description[256];    /**< String variável - Descrição do status */
    uint16_t counter;         /**< 16 bits - Contador de operação (inicia em 0) */
    uint16_t exception_timer; /**< 16 bits - 0 se não usado */
    uint16_t estimated_time;  /**< 16 bits - 0 se não usado */
    char load_list_ratio[3];  /**< 3 caracteres ASCII - Progresso "000" a "100" */
} __attribute__((packed)) lus_data_t;

/**
 * @brief Estrutura de arquivo LUR (Load Upload Request)
 *
 * Contém a requisição de upload recebida do GSE, incluindo nome do arquivo
 * de firmware e part number do software a ser carregado.
 *
 * @note BC-LLR-33: O arquivo .LUR recebido do GSE deve ser preenchido com os seguintes campos:
 * comprimento do .LUR (32 bits), versão de protocolo (16bits - "A4"), número de arquivos a serem
 * recebidos (16bits - no caso apenas 1), comprimento da string do nome do arquivo a ser carregado (8 bits),
 * string do nome do arquivo a ser carregado (até 256 bytes), tamanho da string com PN (8 bits),
 * string com PN (até 256 bytes)
 */
typedef struct
{
    uint32_t file_length;            /**< 32 bits - Comprimento total do arquivo LUR */
    char protocol_version[2];        /**< 16 bits - Versão do protocolo (A4) */
    uint16_t num_header_files;       /**< 16 bits - Número de arquivos header */
    uint8_t header_file_length;      /**< 8 bits - Comprimento do nome do arquivo header */
    char header_filename[256];       /**< String - Nome do arquivo header (até 256 bytes) */
    uint8_t load_part_number_length; /**< 8 bits - Comprimento do part number */
    char load_part_number[256];      /**< String - Part number do software (até 256 bytes) */
} __attribute__((packed)) lur_data_t;

/**
 * @brief Inicializa estrutura LUI (Load Upload Information)
 *
 * Preenche a estrutura LUI com código de status e descrição fornecidos,
 * configurando também os campos fixos (versão de protocolo e tamanho).
 *
 * @param[out] lui Ponteiro para estrutura LUI a ser inicializada
 * @param[in] status_code Código de status ARINC da operação
 * @param[in] description String descritiva do status (máximo 255 caracteres)
 * @return 0 em sucesso, -1 em caso de parâmetros inválidos
 */
int init_lui(lui_data_t *lui, arinc_op_status_code_t status_code, const char *description);

/**
 * @brief Inicializa estrutura LUS (Load Upload Status)
 *
 * Preenche a estrutura LUS com informações de progresso da operação,
 * incluindo contador, razão de progresso e descrição.
 *
 * @param[out] lus Ponteiro para estrutura LUS a ser inicializada
 * @param[in] status_code Código de status ARINC da operação
 * @param[in] description String descritiva do status (máximo 255 caracteres)
 * @param[in] counter Contador de operação (incrementado a cada envio)
 * @param[in] ratio String com 3 caracteres ASCII indicando progresso ("000" a "100")
 * @return 0 em sucesso, -1 em caso de parâmetros inválidos
 */
int init_lus(lus_data_t *lus, arinc_op_status_code_t status_code,
             const char *description, uint16_t counter, const char *ratio);

/**
 * @brief Faz parsing de buffer contendo arquivo LUR (Load Upload Request)
 *
 * Extrai os campos do arquivo LUR recebido do GSE, incluindo nome do arquivo
 * de firmware e part number. Valida o formato e tamanhos dos campos.
 *
 * @param[in] buf Buffer contendo dados do arquivo LUR em formato binário
 * @param[in] len Tamanho do buffer em bytes
 * @param[out] out Ponteiro para estrutura LUR onde os dados serão armazenados
 * @return 0 em sucesso, -1 em caso de erro de formato ou parâmetros inválidos
 */
int parse_lur(const uint8_t *buf, size_t len, lur_data_t *out);
#endif // ARINC_H