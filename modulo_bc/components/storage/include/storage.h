#ifndef STORAGE_H
#define STORAGE_H

#include <stdio.h>
#include "esp_err.h"
#include "esp_spiffs.h"


#define TEMP_MOUNT_POINT "/temp"
#define STORAGE_MOUNT_POINT "/storage"

esp_err_t mount_spiffs(const char *partition_label, const char *mount_point);

FILE *open_temp_file(const char *filename);
void close_temp_file(FILE *temp_file);

ssize_t write_to_temp(FILE *temp_file, const void *data, size_t len);

esp_err_t move_temp_to_storage(const char *filename);

#endif // STORAGE_H
