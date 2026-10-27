#ifndef USB_COMM_H
#define USB_COMM_H

#include <stdint.h>
#include <stdbool.h>
#include "comm_protocol.h"

#define TX_RING_BUFFER_SIZE 2048

void USB_Comm_Init(void); // Iniciar a comunicação USB
bool USB_Comm_QueueTxData(const uint8_t *data, uint16_t len); // Colocar dados na fila de transmissão
void USB_Comm_ProcessTx(void); // Processar a fila de transmissão

/* Callbacks para o usbd_cdc_if.c */
void USB_Comm_ReceiveCallback(uint8_t *Buf, uint32_t *Len);
void USB_Comm_TxCompleted(void);

/* Função para a máquina de estados ler o novo pacote de configuração*/
bool USB_Comm_GetNewConfig(Protocol_ConfigPacket_t *config);

#endif