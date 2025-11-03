#include "state_machine/fsm.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include <string.h>

static const char *TAG = "BC_FSM";

// Definição das variáveis globais compartilhadas entre os estados
int sock = -1;
struct sockaddr_in server_addr;
struct sockaddr_in client_addr;
socklen_t addr_len;
tftp_packet_t req;
ssize_t n;
uint16_t opcode;
char *filename;
lur_data_t lur_file;
unsigned char hash[32];           // SHA-256
auth_keys_t auth_keys;            // Chaves de autenticação
uint8_t upload_failure_count = 0; // Contador de falhas de upload

// Lista de Part Numbers suportados (exemplo - ajustar conforme hardware real)
const char *SUPPORTED_PNS[SUPPORTED_PNS_COUNT] = {
    "EMB-SW-007-137-045",
    "EMB-SW-007-137-046",
    "EMB-SW-007-137-047"};

/**
 * @brief Verifica se um Part Number é suportado
 * @param pn Part Number a verificar
 * @return true se suportado, false caso contrário
 */
bool is_pn_supported(const char *pn)
{
    if (!pn)
        return false;

    for (int i = 0; i < SUPPORTED_PNS_COUNT; i++)
    {
        if (strcmp(pn, SUPPORTED_PNS[i]) == 0)
        {
            return true;
        }
    }
    return false;
}

/**
 * @brief Task principal da máquina de estados
 * @param pvParameters Parâmetros da task (não utilizados)
 */
static void bc_task(void *pvParameters)
{
    ESP_LOGI(TAG, "Iniciando máquina de estados B/C");

    /* BC-LLR-1 - Início no modo operacional
    Ao boot, o módulo B/C deve inicializar o estado INIT e, 
    após verificações (ver BC-LLR-2) migrar automaticamente para OPERATIONAL se não houver sinalização de manutenção
    */
    fsm_state_t cur = ST_INIT;
    const state_ops_t *ops = fsm_get_ops(cur);

    /* BC-LLR-73 - Inicialização de estado
    Ao entrar em um novo estado, a máquina deve executar as rotinas de inicialização
    específicas daquele estado para preparar recursos necessários.
    */
    if (ops && ops->enter)
    {
        ops->enter();
    }

    /* BC-LLR-74 - Ciclo de execução da máquina de estados
    A máquina de estados deve executar continuamente, processando a lógica do estado atual
    e avaliando se há necessidade de transição para outro estado.
    */
    while (1)
    {
        fsm_state_t next = ST_INIT; // fallback seguro

        if (ops && ops->run)
        {
            next = ops->run();
        }

        if(upload_failure_count > MAX_UPLOAD_FAILURES)
        {
            ESP_LOGE(TAG, "Número máximo de falhas de upload excedido (%d) - transicionando para ST_ERROR", upload_failure_count);
            next = ST_ERROR;
        }

        /* BC-LLR-75 - Gerenciamento de transição entre estados
        Quando detectada mudança de estado, a máquina deve:
        (A) Finalizar o estado atual, liberando recursos alocados
        (B) Atualizar o contexto para o novo estado
        (C) Inicializar o novo estado, preparando recursos necessários
        */
        if (next != cur)
        {
            /* (A) Finalizar estado atual */
            if (ops && ops->exit)
            {
                ops->exit();
            }

            /* (B) Atualizar para novo estado */
            cur = next;
            ops = fsm_get_ops(cur);

            /* (C) Inicializar novo estado */
            if (ops && ops->enter)
            {
                ops->enter();
            }
        }

        /* BC-LLR-76 - Intervalo entre ciclos da máquina de estados
        A máquina de estados deve aguardar 50ms entre cada ciclo de execução para
        permitir que outras tarefas do sistema utilizem o processador e 
        para processar eventos assíncronos.
        */
        vTaskDelay(pdMS_TO_TICKS(50));
    }
}

void bc_fsm_start(void)
{
    ESP_LOGI(TAG, "Criando task da máquina de estados");

    /* BC-LLR-77 - Criação da task da máquina de estados
    O B/C deve criar uma task dedicada para executar a máquina de estados com:
    (A) Identificador único
    (B) Pilha de 16KB para suportar operações complexas
    (C) Prioridade 5, para garantir funcionamento correto
    */
    BaseType_t result = xTaskCreate(
        bc_task,       // função da task
        "bc_fsm_task", // nome da task
        16384,         // stack size (aumentado de 4096 para 16384)
        NULL,          // parâmetros
        5,             // prioridade
        NULL           // handle da task
    );

    /* BC-LLR-78 - Validação de criação da task
    O sistema deve verificar se a task da máquina de estados foi criada com sucesso.
    Em caso de falha (tipicamente por falta de memória), deve registrar erro crítico
    e interromper a execução, pois sem a máquina de estados o sistema não pode operar.
    */
    if (result != pdPASS)
    {
        ESP_LOGE(TAG, "Falha ao criar task da FSM - sistema não pode continuar");
        abort(); /* Interrompe execução - sistema não funciona sem a FSM */
    }
    else
    {
        ESP_LOGI(TAG, "Task da FSM criada com sucesso");
    }
}