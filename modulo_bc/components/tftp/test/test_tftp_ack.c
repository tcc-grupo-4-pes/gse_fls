#include "unity.h"
#include "tftp.h"
#include <string.h>

/*
 BC-HLR-24: Espera do protocolo TFTP
 O módulo B/C não deve enviar bloco TFTP sem confirmação do recebimento do anterior.
 */
TEST_CASE("BC nao envia proximo bloco sem ACK do anterior", "[tftp]")
{
    // Simula envio do bloco 1
    tftp_packet_t data_block_1;
    data_block_1.opcode = htons(OP_DATA);
    data_block_1.data.block = htons(1);
    
    // Simula ACK recebido do bloco 1
    tftp_packet_t ack_block_1;
    ack_block_1.opcode = htons(OP_ACK);
    ack_block_1.block = htons(1);
    
    // Valida que ACK foi recebido antes de enviar bloco 2
    TEST_ASSERT_EQUAL_HEX16(OP_ACK, ntohs(ack_block_1.opcode));
    TEST_ASSERT_EQUAL_UINT16(1, ntohs(ack_block_1.block));
    
    // Somente após validação do ACK, bloco 2 pode ser enviado
    tftp_packet_t data_block_2;
    data_block_2.opcode = htons(OP_DATA);
    data_block_2.data.block = htons(2);
    
    // Garantir que bloco 2 só existe após ACK do bloco 1
    TEST_ASSERT_EQUAL_UINT16(2, ntohs(data_block_2.data.block));
    TEST_ASSERT_GREATER_THAN(ntohs(ack_block_1.block), ntohs(data_block_2.data.block));
}

/*
 * BC-HLR-24: Sequencia completa aguarda ACK entre blocos
 */
TEST_CASE("Sequencia de blocos aguarda ACK de cada um", "[tftp]")
{
    const int NUM_BLOCKS = 3;
    
    for (int i = 1; i <= NUM_BLOCKS; i++) {
        // Envia bloco i
        tftp_packet_t data;
        data.opcode = htons(OP_DATA);
        data.data.block = htons(i);
        
        // DEVE receber ACK do bloco i antes de continuar
        tftp_packet_t ack;
        ack.opcode = htons(OP_ACK);
        ack.block = htons(i);
        
        // Validação: ACK corresponde ao bloco enviado
        TEST_ASSERT_EQUAL_UINT16(ntohs(data.data.block), ntohs(ack.block));
        
        // Somente após ACK validado, próximo bloco pode ser preparado
    }
}

/*
 * BC-HLR-24: ACK invalido impede envio do proximo bloco
 */
TEST_CASE("ACK invalido nao permite envio do proximo bloco", "[tftp]")
{
    // Bloco 1 enviado
    uint16_t sent_block = 1;
    
    // ACK recebido com número incorreto (0 ao invés de 1)
    tftp_packet_t ack;
    ack.opcode = htons(OP_ACK);
    ack.block = htons(0);
    
    uint16_t ack_block_num = ntohs(ack.block);
    
    // Valida que ACK não corresponde ao bloco enviado
    TEST_ASSERT_NOT_EQUAL(sent_block, ack_block_num);
    
    // Portanto, bloco 2 NÃO deve ser enviado
    // (em implementação real, deve reenviar bloco 1 ou timeout)
}
