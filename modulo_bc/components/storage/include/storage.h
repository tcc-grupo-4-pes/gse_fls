#ifndef STORAGE_H
#define STORAGE_H

#include <stdio.h>
#include "esp_err.h"
#include "esp_spiffs.h"

#define FIRMWARE_MOUNT_POINT "/firmware"
#define TEMP_FILE_PATH "/firmware/temp.bin"
#define FINAL_FILE_PATH "/firmware/final.bin"

esp_err_t mount_spiffs(const char *partition_label, const char *mount_point);

FILE *open_temp_file(void);
void close_temp_file(FILE *temp_file);

ssize_t write_to_temp(FILE *temp_file, const void *data, size_t len);

esp_err_t finalize_firmware_file(void);

#endif // STORAGE_H
