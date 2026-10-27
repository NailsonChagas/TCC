#ifndef COMM_PROTOCOL_H
#define COMM_PROTOCOL_H

#include <stdint.h>

// Cabeçalhos de protocolo de comunicação
#define HEAD_CONFIG         0x0001
#define HEAD_CONFIG_SUCCESS 0x0002
#define HEAD_CONFIG_FAIL    0x0003
#define HEAD_DATA           0x0004
#define HEAD_SIM_END        0x0005

#pragma pack(push, 1) // Salva o alinhamento atual e define alinhamento de 1 byte para evitar padding entre os campos das estruturas.
typedef struct {
    uint16_t header;
    float vO_max;
    float iL_max;
    float Ad_00;
    float Ad_01;
    float Bd1_0;
    float Ad_10;
    float Ad_11;
    float Bd1_1;
    float fs;
    uint32_t n;
    uint32_t total_steps;
} Protocol_ConfigPacket_t;

typedef struct {
    uint16_t header;
    uint32_t k;
    float iL;
    float vC_val;
} Protocol_DataPacket_t;
#pragma pack(pop) // Restaura a configuração de alinhamento anterior.

#endif // COMM_PROTOCOL_H