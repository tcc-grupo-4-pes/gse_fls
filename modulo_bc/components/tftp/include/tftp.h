#ifndef TFTP_H
#define TFTP_H

#include <stdint.h>
#include <stddef.h>
#include <sys/socket.h>
#include <netinet/in.h>

#include "arinc615a.h"

// TFTP constants
#define TFTP_PORT 69       /**< Porta padrão do protocolo TFTP */
#define BLOCK_SIZE 512     /**< Tamanho do bloco de dados TFTP (BC-LLR-17) */
#define TFTP_RETRY_LIMIT 1 /**< Número máximo de retentativas em caso de timeout */
#define TFTP_TIMEOUT_SEC 2 /**< Timeout em segundos para operações TFTP (BC-LLR-16) */

// TFTP opcodes
#define OP_RRQ 1   /**< Opcode para Read Request */
#define OP_WRQ 2   /**< Opcode para Write Request */
#define OP_DATA 3  /**< Opcode para Data packet */
#define OP_ACK 4   /**< Opcode para Acknowledgment */
#define OP_ERROR 5 /**< Opcode para Error packet */

/**
 * @brief Estrutura de pacote TFTP genérico
 *
 * União que representa todos os tipos de pacotes TFTP (RRQ, WRQ, DATA, ACK, ERROR).
 * O campo opcode determina qual campo da união é válido.
 */
typedef struct
{
    uint16_t opcode; /**< Código de operação TFTP (OP_RRQ, OP_WRQ, OP_DATA, OP_ACK, OP_ERROR) */
    union
    {
        char request[514]; /**< Para RRQ/WRQ: 'filename\0mode\0' */
        struct
        {
            uint16_t block;    /**< Número do bloco de dados */
            uint8_t data[512]; /**< Dados do bloco (até 512 bytes) */
        } data;                /**< Pacote DATA */
        uint16_t block;        /**< Para ACK: número do bloco reconhecido */
        struct
        {
            uint16_t code; /**< Código de erro */
            char msg[512]; /**< Mensagem de erro */
        } error;           /**< Pacote ERROR */
    };
} __attribute__((packed)) tftp_packet_t;

/**
 * @brief Processa Read Request do GSE e envia arquivo LUI
 *
 * Chamada quando o GSE envia RRQ solicitando o arquivo .LUI.
 * Cria socket efêmero (TID), envia ACK(0), monta o arquivo LUI e transmite via DATA packets.
 *
 * @param[in] sock Socket UDP principal do servidor TFTP
 * @param[in] client Endereço do cliente GSE
 * @param[in] filename Nome do arquivo solicitado (deve conter ".LUI")
 *
 * @note BC-LLR-21, BC-LLR-22, BC-LLR-23, BC-LLR-24, BC-LLR-25, BC-LLR-26, BC-LLR-89, BC-LLR-90
 */
void handle_rrq(int sock, struct sockaddr_in *client, char *filename);

/**
 * @brief Processa Write Request do GSE e recebe arquivo LUR
 *
 * Chamada quando o GSE envia WRQ solicitando envio do arquivo .LUR.
 * Cria socket efêmero (TID), envia ACK(0) e recebe os blocos DATA do LUR.
 *
 * @param[in] sock Socket UDP principal do servidor TFTP
 * @param[in] client Endereço do cliente GSE
 * @param[in] filename Nome do arquivo a ser recebido 
 * @param[out] lur_file Estrutura para armazenar os dados do LUR recebido
 *
 * @note BC-LLR-27, BC-LLR-28, BC-LLR-29, BC-LLR-30, BC-LLR-89, BC-LLR-91, BC-LLR-92, BC-LLR-93
 */
void handle_wrq(int sock, struct sockaddr_in *client, char *filename, lur_data_t *lur_file);

/**
 * @brief Envia Write Request ao GSE para transmitir arquivo LUS
 *
 * Chamada pelo B/C para iniciar transferência do arquivo .LUS ao GSE.
 * Envia WRQ, aguarda ACK(0), transmite DATA packet e aguarda ACK final.
 *
 * @param[in] sock Socket UDP para comunicação TFTP
 * @param[in] client_addr Endereço do servidor GSE
 * @param[in] lus_filename Nome do arquivo LUS (ex: "file.LUS")
 * @param[in] lus_data Estrutura contendo os dados do LUS a serem enviados
 *
 * @note BC-LLR-31, BC-LLR-32, BC-LLR-33, BC-LLR-34, BC-LLR-35, BC-LLR-36, BC-LLR-89, BC-LLR-94, BC-LLR-95
 */
void make_wrq(int sock, struct sockaddr_in *client_addr, const char *lus_filename, const lus_data_t *lus_data);

/**
 * @brief Envia Read Request ao GSE para receber arquivo de firmware
 *
 * Chamada pelo B/C para solicitar download de firmware do GSE.
 * Envia RRQ, aguarda ACK(0), recebe DATA packets, calcula SHA-256 e salva em temp.bin.
 *
 * @param[in] sock Socket UDP para comunicação TFTP
 * @param[in] client_addr Endereço do servidor GSE
 * @param[in] filename Nome do arquivo de firmware solicitado
 * @param[out] hash Buffer para armazenar o SHA-256 calculado (32 bytes)
 *
 * @note BC-LLR-37, BC-LLR-61, BC-LLR-89, BC-LLR-96, BC-LLR-97, BC-LLR-98, BC-LLR-99,
 *       BC-LLR-100, BC-LLR-101, BC-LLR-102, BC-LLR-103
 */
void make_rrq(int sock, struct sockaddr_in *client_addr, const char *filename, unsigned char *hash);

#endif // TFTP_H
