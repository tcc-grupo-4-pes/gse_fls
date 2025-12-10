idf_component_register(SRCS "tftp.c"
                    REQUIRES mbedtls arinc615a storage state_machine
                    INCLUDE_DIRS "include")
