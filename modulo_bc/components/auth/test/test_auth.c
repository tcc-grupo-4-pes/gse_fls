#include "unity.h"
#include "auth.h"
#include "storage.h"

#include <stdio.h>
static void remove_if_exists(const char *path)
{
    remove(path);
}

static void assert_file_non_empty(const char *path)
{
    FILE *file = fopen(path, "rb");
    TEST_ASSERT_NOT_NULL_MESSAGE(file, "Arquivo nao encontrado na particao keys");

    unsigned char byte = 0;
    size_t read_len = fread(&byte, 1, 1, file);
    fclose(file);

    TEST_ASSERT_NOT_EQUAL_MESSAGE(0, read_len, "Arquivo criado, mas sem conteudo");
}

TEST_CASE("auth_write_static_keys grava arquivos na particao keys", "[auth]")
{
    TEST_ASSERT_EQUAL(ESP_OK, mount_spiffs("keys", KEYS_MOUNT_POINT));

    remove_if_exists(BC_KEY_FILE);
    remove_if_exists(GSE_KEY_FILE);

    TEST_ASSERT_EQUAL(ESP_OK, auth_write_static_keys());

    assert_file_non_empty(BC_KEY_FILE);
    assert_file_non_empty(GSE_KEY_FILE);
}
