/**
 * @file state_table.c
 * @brief Tabela de mapeamento de estados para operações (vtable)
 *
 * Este arquivo define a tabela que mapeia cada estado da FSM para sua
 * respectiva estrutura de operações (enter, run, exit), implementando
 * o padrão State com virtual table.
 */

#include <stddef.h>
#include "state_machine/fsm.h"

// Declarações forward dos estados
extern const state_ops_t state_init_ops;
extern const state_ops_t state_operational_ops;
extern const state_ops_t state_maint_wait_ops;
extern const state_ops_t state_upload_prep_ops;
extern const state_ops_t state_uploading_ops;
extern const state_ops_t state_verify_ops;
extern const state_ops_t state_save_ops;
extern const state_ops_t state_teardown_ops;
extern const state_ops_t state_error_ops;

/**
 * @brief Tabela de operações para cada estado
 *
 * Array estático que mapeia cada enumeração de estado (fsm_state_t)
 * para seu respectivo conjunto de operações (state_ops_t).
 * Permite lookup O(1) das operações de um estado.
 */
static const state_ops_t *state_table[ST__COUNT] = {
    [ST_INIT] = &state_init_ops,
    [ST_OPERATIONAL] = &state_operational_ops,
    [ST_MAINT_WAIT] = &state_maint_wait_ops,
    [ST_UPLOAD_PREP] = &state_upload_prep_ops,
    [ST_UPLOADING] = &state_uploading_ops,
    [ST_VERIFY] = &state_verify_ops,
    [ST_SAVE] = &state_save_ops,
    [ST_TEARDOWN] = &state_teardown_ops,
    [ST_ERROR] = &state_error_ops,
};

const state_ops_t *fsm_get_ops(fsm_state_t st)
{
    if (st >= 0 && st < ST__COUNT)
    {
        return state_table[st];
    }
    return NULL;
}