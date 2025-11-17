/**
 * @file storage.c
 * @brief Implementação do componente de gerenciamento de armazenamento SPIFFS
 *
 * Este arquivo implementa as funções de montagem de partições SPIFFS,
 * manipulação de arquivos temporários e finalização de arquivos de firmware.
 *
 * @note BC-LLR-49, BC-LLR-44, BC-LLR-45, BC-LLR-66, BC-LLR-67
 */

#include "storage.h"
#include <unistd.h> // unlink

#include "esp_log.h"
static const char *TAG = "storage";

/**
 * @brief Monta uma partição SPIFFS no sistema de arquivos virtual
 *
 * Registra uma partição SPIFFS no VFS (Virtual File System) do ESP32 e a monta
 * no ponto especificado. Se a montagem falhar, tenta formatar automaticamente a
 * partição. Após montagem bem-sucedida, exibe informações sobre espaço total e usado.
 *
 * @param[in] partition_label Rótulo da partição SPIFFS definido em partitions.csv (ex: "keys", "firmware")
 * @param[in] mount_point Caminho absoluto no VFS onde a partição será montada (ex: "/keys", "/firmware")
 *
 * @return
 *     - ESP_OK: Partição montada com sucesso
 *     - ESP_FAIL: Falha ao registrar ou montar a partição
 *
 * @note BC-LLR-49
 */
esp_err_t mount_spiffs(const char *partition_label, const char *mount_point)
{
    ESP_LOGI(TAG, "Mounting SPIFFS partition %s at %s", partition_label, mount_point);

    esp_vfs_spiffs_conf_t conf = {
        .base_path = mount_point,
        .partition_label = partition_label,
        .max_files = 5,
        .format_if_mount_failed = true};

    esp_err_t ret = esp_vfs_spiffs_register(&conf);
    if (ret != ESP_OK)
    {
        ESP_LOGE(TAG, "Failed to mount SPIFFS (%s)", esp_err_to_name(ret));
        return ret;
    }

    size_t total = 0, used = 0;
    ret = esp_spiffs_info(partition_label, &total, &used);
    if (ret == ESP_OK)
    {
        ESP_LOGI(TAG, "Partition size: total: %d, used: %d", total, used);
    }

    return ESP_OK;
}

/**
 * @brief Abre arquivo temporário para escrita de firmware
 *
 * Cria (ou sobrescreve se existir) o arquivo temp.bin na partição de firmware
 * e o abre em modo escrita binária. Este arquivo é usado durante o estado UPLOADING
 * para armazenar o firmware sendo recebido via TFTP antes da verificação de integridade.
 *
 * @return
 *     - Ponteiro FILE* válido: Arquivo aberto com sucesso
 *     - NULL: Falha ao abrir o arquivo
 *
 * @note O arquivo deve ser fechado com close_temp_file() após uso
 */
FILE *open_temp_file(void)
{
    FILE *temp_file = fopen(TEMP_FILE_PATH, "wb");
    ESP_LOGI(TAG, "Opened temporary file: %s", TEMP_FILE_PATH);
    return temp_file;
}

/**
 * @brief Fecha arquivo temporário
 *
 * Fecha o arquivo temporário aberto por open_temp_file() e libera recursos associados.
 * Função segura para chamada com ponteiro NULL (não realiza nenhuma operação).
 *
 * @param[in] temp_file Ponteiro para arquivo a ser fechado (pode ser NULL)
 */
void close_temp_file(FILE *temp_file)
{
    if (temp_file)
    {
        fclose(temp_file);
    }
}

/**
 * @brief Escreve dados no arquivo temporário
 *
 * Grava um bloco de dados no arquivo temporário de firmware. Esta função é chamada
 * repetidamente durante o recebimento de pacotes TFTP no estado UPLOADING para
 * armazenar cada bloco de dados do firmware.
 *
 * @param[in] temp_file Ponteiro para arquivo temporário aberto
 * @param[in] data Buffer contendo os dados a serem escritos
 * @param[in] len Número de bytes a escrever do buffer
 *
 * @return Número de bytes efetivamente escritos (pode ser menor que len em caso de erro)
 */
ssize_t write_to_temp(FILE *temp_file, const void *data, size_t len)
{
    size_t written = fwrite(data, 1, len, temp_file);
    return written;
}

/**
 * @brief Finaliza arquivo de firmware renomeando temp.bin para final.bin
 *
 * Executa a sequência de operações necessárias no estado SAVE:
 * 1. Remove o arquivo final.bin existente (se presente)
 * 2. Renomeia temp.bin para final.bin
 *
 * Se o arquivo final.bin não existir, a remoção falha mas a execução continua.
 * Se a renomeação falhar, o sistema deve transitar para o estado ERROR.
 *
 * @return
 *     - ESP_OK: Arquivo finalizado com sucesso (temp.bin agora é final.bin)
 *     - ESP_FAIL: Falha ao renomear arquivo temporário
 *
 * @note BC-LLR-44, BC-LLR-45, BC-LLR-66, BC-LLR-67
 */
esp_err_t finalize_firmware_file(void)
{
    ESP_LOGI(TAG, "Finalizing firmware file: temp.bin -> final.bin");

    /* BC-LLR-44 - Excluir arquivo para carregamento do novo firmware
    No estado SAVE, o software do B/C deve inicialmente apagar o arquivo salvo de firmware
    final.bin salvo atualmente na partição fs_main da memória flash
    */
    if (unlink(FINAL_FILE_PATH) == 0)
    {
        ESP_LOGI(TAG, "Removed existing final.bin");
    }
    else
    {
        /* BC-LLR-66 - Erro de excluir arquivo final anterior
        No estado SAVE, caso a remoção do arquivo final na partição falhar(não existe arquivo final),
        o software deve continuar sua execução e dar um log
        */
        ESP_LOGW(TAG, "No existing final.bin to remove (or removal failed)");
    }

    /* BC-LLR-45 - Renomear arquivo de firmware temporário
    No estado SAVE,após apagar o antigo arquivo final.bin corretamente,
    o software do B/C deve renomear o arquivo temporário para final.bin
    na partição fs_main da memória flash
    */
    if (rename(TEMP_FILE_PATH, FINAL_FILE_PATH) != 0)
    {
        /* BC-LLR-67 - Erro de renomear o arquivo temporário para final
        No estado SAVE, caso haja erro ao renomear o arquivo temporário para final na partição firmware,
        o software deve ir para o estado de ERROR e parar a execução
        */
        ESP_LOGE(TAG, "Failed to rename temp.bin to final.bin");
        return ESP_FAIL;
    }

    ESP_LOGI(TAG, "Successfully renamed temp.bin to final.bin");
    return ESP_OK;
}
