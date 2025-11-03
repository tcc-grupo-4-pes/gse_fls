#ifndef FSM_H
#define FSM_H

#include <stdint.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include "tftp.h"
#include "arinc.h"
#include "auth.h"

/**
 * @brief Estados da máquina de estados B/C
 */
typedef enum
{
    ST_INIT = 0,
    ST_OPERATIONAL,
    ST_MAINT_WAIT,
    ST_UPLOAD_PREP,
    ST_UPLOADING,
    ST_VERIFY,
    ST_SAVE,
    ST_TEARDOWN,
    ST_ERROR,
    ST__COUNT
} fsm_state_t;

/**
 * @brief Estrutura de operações para cada estado (vtable)
 */
typedef struct
{
    void (*enter)(void);      // setup rápido do estado
    fsm_state_t (*run)(void); // executa a lógica mínima e retorna o próximo estado
    void (*exit)(void);       // limpeza
    const char *name;         // nome do estado para logs
} state_ops_t;

/**
 * @brief Inicializa a FSM criando a task principal e iniciando no estado ST_INIT
 */
void bc_fsm_start(void);

/**
 * @brief Obtém as operações para um estado específico
 * @param st Estado para o qual se deseja obter as operações
 * @return Ponteiro para a estrutura de operações do estado
 */
const state_ops_t *fsm_get_ops(fsm_state_t st);

/**
 * @brief Variáveis globais compartilhadas entre os estados da FSM
 */
extern int sock;
extern struct sockaddr_in server_addr;
extern struct sockaddr_in client_addr;
extern socklen_t addr_len;
extern tftp_packet_t req;
extern ssize_t n;
extern uint16_t opcode;
extern char *filename;
extern lur_data_t lur_file;
extern unsigned char hash[32];       // SHA-256
extern auth_keys_t auth_keys;        // Chaves de autenticação
extern uint8_t upload_failure_count; // Contador de falhas de upload

// Lista de Part Numbers (PNs) suportados pelo módulo B/C
#define SUPPORTED_PNS_COUNT 3
extern const char *SUPPORTED_PNS[SUPPORTED_PNS_COUNT];
#define MAX_UPLOAD_FAILURES 2 // Máximo de tentativas falhas antes de ERROR

// Função para verificar se PN é suportado
bool is_pn_supported(const char *pn);


#endif /* FSM_H */