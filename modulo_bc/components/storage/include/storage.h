/**
 * @file storage.h
 * @brief Abstração de acesso a partições SPIFFS para chaves e firmware
 *
 * Este módulo fornece funções de alto nível para gerenciamento de partições SPIFFS
 * no ESP32, incluindo montagem de partições, manipulação de arquivos temporários
 * durante o upload de firmware, e finalização de arquivos persistentes.
 *
 * Funcionalidades principais:
 * - Montagem de partições SPIFFS (keys, firmware)
 * - Abertura e escrita em arquivos temporários
 * - Renomeação e finalização de arquivos de firmware
 *
 * @note BC-LLR-49, BC-LLR-44, BC-LLR-45, BC-LLR-66, BC-LLR-67
 */

#ifndef STORAGE_H
#define STORAGE_H

#include <stdio.h>
#include "esp_err.h"
#include "esp_spiffs.h"

#define FIRMWARE_MOUNT_POINT "/firmware"      /**< Ponto de montagem da partição de firmware */
#define TEMP_FILE_PATH "/firmware/temp.bin"   /**< Caminho do arquivo temporário durante upload */
#define FINAL_FILE_PATH "/firmware/final.bin" /**< Caminho do arquivo final de firmware */

/* BC-LLR-49 - Tabela de partições
O módulo B/C deve usar a tabela de partição para flash de 4 MB com: bootloader + partition table (32 KB),
nvs (24 KB), phy_init (4 KB), factory (1 MB), keys (64 KB, SPIFFS) e firmware (~2,86 MB, SPIFFS)
*/

/**
 * @brief Monta uma partição SPIFFS
 *
 * Registra e monta uma partição SPIFFS no sistema de arquivos virtual (VFS) do ESP32.
 * Formata automaticamente a partição se a montagem falhar.
 *
 * @param[in] partition_label Rótulo da partição SPIFFS (ex: "keys", "firmware")
 * @param[in] mount_point Caminho de montagem no VFS (ex: "/keys", "/firmware")
 *
 * @return
 *     - ESP_OK: Partição montada com sucesso
 *     - ESP_FAIL: Falha ao montar ou registrar a partição
 *
 * @note BC-LLR-49
 */
esp_err_t mount_spiffs(const char *partition_label, const char *mount_point);

/**
 * @brief Abre arquivo temporário para escrita de firmware
 *
 * Cria e abre o arquivo temp.bin na partição de firmware para escrita binária.
 * Usado durante o estado UPLOADING para armazenar o firmware recebido via TFTP.
 *
 * @return
 *     - Ponteiro FILE* válido se sucesso
 *     - NULL se falha ao abrir o arquivo
 */
FILE *open_temp_file(void);
/**
 * @brief Fecha arquivo temporário
 *
 * Fecha o arquivo temporário aberto por open_temp_file() e libera recursos.
 *
 * @param[in] temp_file Ponteiro para arquivo a ser fechado (pode ser NULL)
 */
void close_temp_file(FILE *temp_file);

/**
 * @brief Escreve dados no arquivo temporário
 *
 * Grava um bloco de dados no arquivo temporário de firmware.
 *
 * @param[in] temp_file Ponteiro para arquivo temporário aberto
 * @param[in] data Buffer de dados a serem escritos
 * @param[in] len Número de bytes a escrever
 *
 * @return Número de bytes efetivamente escritos
 */
ssize_t write_to_temp(FILE *temp_file, const void *data, size_t len);

/**
 * @brief Finaliza arquivo de firmware renomeando temp.bin para final.bin
 *
 * Remove o arquivo final.bin existente e renomeia temp.bin para final.bin.
 * Executa as operações necessárias no estado SAVE da máquina de estados.
 *
 * @return
 *     - ESP_OK: Arquivo finalizado com sucesso
 *     - ESP_FAIL: Falha ao renomear arquivo temporário
 *
 * @note BC-LLR-44, BC-LLR-45, BC-LLR-66, BC-LLR-67
 */
esp_err_t finalize_firmware_file(void);

#endif // STORAGE_H
