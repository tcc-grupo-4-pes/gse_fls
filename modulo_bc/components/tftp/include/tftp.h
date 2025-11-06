#ifndef TFTP_H
#define TFTP_H

#include <stdint.h>
#include <stddef.h>
#include <sys/socket.h>
#include <netinet/in.h>

#include "arinc.h"

// TFTP constants
#define TFTP_PORT 69
#define BLOCK_SIZE 512 /*BC-LLR-17*/
#define TFTP_RETRY_LIMIT 1
#define TFTP_TIMEOUT_SEC 2 /*BC-LLR-16*/


// TFTP opcodes
#define OP_RRQ 1
#define OP_WRQ 2
#define OP_DATA 3
#define OP_ACK 4
#define OP_ERROR 5

// TFTP pacote
typedef struct
{
    uint16_t opcode;
    union
    {
        char request[514]; // 'filename\0mode\0'
        struct
        {
            uint16_t block;
            uint8_t data[512];
        } data;
        uint16_t block; // For ACK
        struct
        {
            uint16_t code;
            char msg[512];
        } error;
    };
} __attribute__((packed)) tftp_packet_t;

// API exported by the tftp component
void handle_rrq(int sock, struct sockaddr_in *client, char *filename);
void handle_wrq(int sock, struct sockaddr_in *client, char *filename, lur_data_t *lur_file);
void make_wrq(int sock, struct sockaddr_in *client_addr, const char *lus_filename, const lus_data_t *lus_data);
void make_rrq(int sock, struct sockaddr_in *client_addr, const char *filename, unsigned char *hash);

#endif // TFTP_H
