#ifndef ARINC_H
#define ARINC_H

#include <stdint.h>
#include <stddef.h>

/*BC-LLR-25
O software do módulo B/C deve usar os códigos de status definidos no
Protocolo ARINC615A(conforme tabela do slide 38 do treinamento)
*/
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

/* BC-LLR-26
O arquivo .LUI deve conter campos para comprimento do .LUI (32 bits), versão do protocolo (16 bits - "A4"), 
Status de aceitação da operação (16bits), uma string de descrição do status(até 256 bytes) e o 
tamanho da string de descrição(8 bits)
*/
typedef struct
{
    uint32_t file_length;     // 32 bits - Total length of LUI file
    char protocol_version[2]; // 16 bits - Protocol version (A4)
    uint16_t status_code;     // 16 bits - ARINC status code
    uint8_t desc_length;      // 8 bits - Length of description
    char description[256];    // Variable string - Status description
} __attribute__((packed)) lui_data_t;

/*BC-LLR-31
O arquivo .LUS deve conter campos para comprimento do .LUS (32 bits),
versão do protocolo (16 bits - "A4"), Status de aceitação da operação (16bits), 
uma string de descrição do status(até 256 bytes) e o tamanho da string de descrição(8 bits), 
contador(16 bits), exception timer e expection time(16 bits cada), 
Razão(%) da lista de Load(24 bits - 3 ASCII)
*/
typedef struct
{
    uint32_t file_length;     // 32 bits - Total length of LUS file
    char protocol_version[2]; // 16 bits - Protocol version (A4)
    uint16_t status_code;     // 16 bits - ARINC status code
    uint8_t desc_length;      // 8 bits - Length of description
    char description[256];    // Variable string - Status description
    uint16_t counter;         // 16 bits - Operation counter (starts at 0)
    uint16_t exception_timer; // 16 bits - 0 if not used
    uint16_t estimated_time;  // 16 bits - 0 if not used
    char load_list_ratio[3];  // 3 ASCII chars - Progress "000" to "100"
} __attribute__((packed)) lus_data_t;

/* BC-LLR-33
O arquivo .LUR recebido do GSE deve ser preenchido com os seguintes campos: 
comprimento do .LUR(32 bits), versão de protocolo(16bits - "A4"), número de arquivos a serem 
recebidos(16bits - no caso apenas 1), comprimento da string do nome do arquivo a ser carregado(8 bits), 
string do nome do arquivo a ser carregado(até 256 bytes), tamanho da string com PN (8 bits), 
string com PN(até 256 bytes) 
*/
typedef struct
{
    uint32_t file_length;       // 32 bits - Total length of LUR file
    char protocol_version[2];   // 16 bits - Protocol version (A4)
    uint16_t num_header_files;  // 16 bits - Number of header files
    uint8_t header_file_length; // 8 bits - Length of header file name
    char header_filename[256];
    uint8_t load_part_number_length; // 8 bits - Length of load part number
    char load_part_number[256];
} __attribute__((packed)) lur_data_t;

int init_lui(lui_data_t *lui, arinc_op_status_code_t status_code, const char *description);

int init_lus(lus_data_t *lus, arinc_op_status_code_t status_code,
             const char *description, uint16_t counter, const char *ratio);

int parse_lur(const uint8_t *buf, size_t len, lur_data_t *out);
#endif // ARINC_H