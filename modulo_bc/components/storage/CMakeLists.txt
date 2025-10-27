idf_component_register(SRCS "storage.c"
                    REQUIRES spiffs nvs_flash
                    INCLUDE_DIRS "include")
