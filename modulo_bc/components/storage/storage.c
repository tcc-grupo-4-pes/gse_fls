#include "storage.h"

#include <string.h> // snprintf, memset
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

FILE *open_temp_file(const char *filename)
{
    char temp_path[512];
    snprintf(temp_path, sizeof(temp_path), "%s/%s", TEMP_MOUNT_POINT, filename);

    FILE *temp_file = fopen(temp_path, "wb");
    if (!temp_file)
    {
        ESP_LOGE(TAG, "Failed to open temporary file for write: %s", temp_path);
        return NULL;
    }

    ESP_LOGI(TAG, "Opened temporary file: %s", temp_path);
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

esp_err_t move_temp_to_storage(const char *filename)
{
    char temp_path[512];
    char final_path[512];
    snprintf(temp_path, sizeof(temp_path), "%s/%s", TEMP_MOUNT_POINT, filename);
    snprintf(final_path, sizeof(final_path), "%s/%s", STORAGE_MOUNT_POINT, filename);

    FILE *src = fopen(temp_path, "rb");
    if (!src)
    {
        ESP_LOGE(TAG, "Failed to open temporary file for copy: %s", temp_path);
        return ESP_FAIL;
    }

    FILE *dst = fopen(final_path, "wb");
    if (!dst)
    {
        ESP_LOGE(TAG, "Failed to open destination file: %s", final_path);
        fclose(src);
        return ESP_FAIL;
    }

    uint8_t buf[1024];
    size_t r;
    esp_err_t ret = ESP_OK;

    while ((r = fread(buf, 1, sizeof(buf), src)) > 0)
    {
        if (fwrite(buf, 1, r, dst) != r)
        {
            ESP_LOGE(TAG, "Error writing to %s", final_path);
            ret = ESP_FAIL;
            break;
        }
    }

    fclose(src);
    fclose(dst);

    if (ret == ESP_OK)
    {
        // Remove temporary file only if copy was successful
        if (unlink(temp_path) != 0)
        {
            ESP_LOGW(TAG, "Failed to remove temporary file %s", temp_path);
        }
        else
        {
            ESP_LOGI(TAG, "File moved successfully to storage: %s", final_path);
        }
    }

    return ret;
}
