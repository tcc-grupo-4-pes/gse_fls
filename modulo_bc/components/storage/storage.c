#include "storage.h"
#include <unistd.h> // unlink

#include "esp_log.h"
static const char *TAG = "storage";

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

FILE *open_temp_file(void)
{
    FILE *temp_file = fopen(TEMP_FILE_PATH, "wb");
    if (!temp_file)
    {
        ESP_LOGE(TAG, "Failed to open temporary file for write: %s", TEMP_FILE_PATH);
        return NULL;
    }

    ESP_LOGI(TAG, "Opened temporary file: %s", TEMP_FILE_PATH);
    return temp_file;
}

void close_temp_file(FILE *temp_file)
{
    if (temp_file)
    {
        fclose(temp_file);
    }
}

ssize_t write_to_temp(FILE *temp_file, const void *data, size_t len)
{
    size_t written = fwrite(data, 1, len, temp_file);
    return written;
}

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
