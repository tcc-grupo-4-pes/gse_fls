idf_component_register(SRCS "main.c"
                    REQUIRES spiffs esp_wifi nvs_flash mbedtls 
                    INCLUDE_DIRS ".")