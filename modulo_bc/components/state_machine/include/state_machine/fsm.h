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
 *
 * Enumeração que define todos os estados possíveis da FSM do módulo B/C.
 */
typedef enum
{
    ST_INIT = 0,    /**< Estado inicial: inicializa NVS, SPIFFS e chaves */
    ST_OPERATIONAL, /**< Modo operacional normal: aguarda botão de manutenção */
    ST_MAINT_WAIT,  /**< Modo manutenção: AP Wi-Fi ativo, aguarda conexão GSE */
    ST_UPLOAD_PREP, /**< Preparação upload: envia LUI/LUS e recebe LUR */
    ST_UPLOADING,   /**< Recebendo firmware: download via TFTP com SHA-256 */
    ST_VERIFY,      /**< Verificação: compara SHA-256 calculado vs esperado */
    ST_SAVE,        /**< Salvamento: renomeia temp.bin para final.bin */
    ST_TEARDOWN,    /**< Finalização: envia LUS final e limpa variáveis */
    ST_ERROR,       /**< Estado de erro: remove temp.bin e encerra execução */
    ST__COUNT       /**< Contador total de estados */
} fsm_state_t;

/**
 * @brief Estrutura de operações para cada estado (vtable)
 *
 * Define os callbacks de ciclo de vida de cada estado da FSM.
 * Implementa o padrão State usando virtual table (vtable).
 */
typedef struct
{
    void (*enter)(void);      /**< Callback de entrada: inicialização do estado */
    fsm_state_t (*run)(void); /**< Callback de execução: lógica principal, retorna próximo estado */
    void (*exit)(void);       /**< Callback de saída: limpeza e finalização */
    const char *name;         /**< Nome do estado para logging */
} state_ops_t;

/**
 * @brief Inicializa a FSM criando a task principal e iniciando no estado ST_INIT
 *
 * Cria uma task FreeRTOS dedicada que executa o loop principal da máquina de estados.
 * A FSM inicia automaticamente no estado ST_INIT.
 *
 * @note BC-LLR-1
 */
void bc_fsm_start(void);

/**
 * @brief Obtém as operações para um estado específico
 *
 * Retorna o ponteiro para a vtable do estado solicitado.
 *
 * @param[in] st Estado para o qual se deseja obter as operações
 * @return Ponteiro para a estrutura de operações do estado, ou NULL se inválido
 */
const state_ops_t *fsm_get_ops(fsm_state_t st);

/**
 * @brief Variáveis globais compartilhadas entre os estados da FSM
 *
 * Estas variáveis mantêm o contexto global da FSM e são acessíveis por todos os estados.
 */
extern int sock;                       /**< Socket UDP principal para comunicação TFTP */
extern struct sockaddr_in server_addr; /**< Endereço do servidor (B/C) */
extern struct sockaddr_in client_addr; /**< Endereço do cliente (GSE) */
extern socklen_t addr_len;             /**< Tamanho da estrutura de endereço */
extern tftp_packet_t req;              /**< Buffer para pacotes TFTP recebidos */
extern ssize_t n;                      /**< Bytes recebidos na última operação */
extern uint16_t opcode;                /**< Opcode do último pacote TFTP recebido */
extern char *filename;                 /**< Nome do arquivo da requisição TFTP atual */
extern lur_data_t lur_file;            /**< Dados do arquivo LUR (metadados do firmware) */
extern unsigned char hash[32];         /**< Hash SHA-256 calculado do firmware */
extern auth_keys_t auth_keys;          /**< Chaves de autenticação BC/GSE */
extern uint8_t upload_failure_count;   /**< Contador de falhas de upload */

/**
 * @brief Número de Part Numbers (PNs) de software suportados
 * @note BC-LLR-103
 */
#define SUPPORTED_PNS_COUNT 3

/** @brief Lista de Part Numbers de software compatíveis com o módulo B/C */
extern const char *SUPPORTED_PNS[SUPPORTED_PNS_COUNT];

/** @brief Part Number do hardware atual do módulo B/C */
extern const char *HW_PN;

/** @brief Máximo de tentativas de upload falhas antes de transitar para ERROR */
#define MAX_UPLOAD_FAILURES 2

/**
 * @brief Verifica se um Part Number de software é suportado
 *
 * Compara o PN fornecido com a lista de PNs compatíveis.
 *
 * @param[in] pn String contendo o Part Number a ser verificado
 * @return true se o PN é suportado, false caso contrário
 * @note BC-LLR-103
 */
bool is_pn_supported(const char *pn);

/**
 * @brief Reseta todas as variáveis globais da FSM
 *
 * Limpa estruturas de dados (lur_file, hash, req), reseta ponteiros,
 * contadores e estado de autenticação. Chamada no estado TEARDOWN.
 *
 * @note BC-LLR-47
 */
void state_teardown_reset_globals(void);

#endif /* FSM_H */