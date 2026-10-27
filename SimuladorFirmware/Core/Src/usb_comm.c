#include "usb_comm.h"
#include "usbd_cdc_if.h"
#include <string.h>

/**
 * @brief Buffer circular para armazenamento dos dados pendentes de transmissão USB.
 */
static uint8_t tx_buffer[TX_RING_BUFFER_SIZE];

/**
 * @brief Índice de inserção de dados no buffer circular.
 *
 * Indica a próxima posição disponível para escrita.
 */
static volatile uint16_t tx_head = 0;

/**
 * @brief Índice de leitura de dados do buffer circular.
 *
 * Indica o próximo byte pendente de transmissão.
 */
static volatile uint16_t tx_tail = 0;

/**
 * @brief Indica se existe uma transmissão USB em andamento.
 */
static volatile bool is_transmitting = false;

/**
 * @brief Armazena o último pacote de configuração recebido do computador.
 */
static Protocol_ConfigPacket_t rx_config;

/**
 * @brief Indica a disponibilidade de uma nova configuração recebida.
 */
static volatile bool new_config_received = false;

/**
 * @brief Inicializa o módulo de comunicação USB.
 *
 * Reinicializa os índices do buffer circular e as flags de controle
 * de transmissão e recepção de configurações.
 */
void USB_Comm_Init(void) {
    tx_head = 0;
    tx_tail = 0;
    is_transmitting = false;
    new_config_received = false;
}

/**
 * @brief Adiciona dados à fila de transmissão USB.
 *
 * Insere os dados recebidos no buffer circular. Caso o espaço disponível
 * seja insuficiente, descarta os dados mais antigos até permitir a
 * inserção do novo conteúdo.
 *
 * Antes de inserir os dados, tenta iniciar o envio de conteúdo pendente
 * quando não há uma transmissão em andamento.
 *
 * @param data Ponteiro para os dados que serão enfileirados.
 * @param len Quantidade de bytes a serem inseridos.
 *
 * @return true se os dados forem aceitos pela fila.
 * @return false se o tamanho solicitado for maior ou igual à capacidade
 *         total do buffer circular.
 */
bool USB_Comm_QueueTxData(const uint8_t *data, uint16_t len) {
    if (len >= TX_RING_BUFFER_SIZE) return false;

    if (!is_transmitting) {
        USB_Comm_ProcessTx();
    }

    uint16_t free_space = (tx_tail <= tx_head) ?
                          (TX_RING_BUFFER_SIZE - tx_head + tx_tail - 1) :
                          (tx_tail - tx_head - 1);

    if (len > free_space) {
        uint16_t bytes_to_discard = len - free_space;
        tx_tail = (tx_tail + bytes_to_discard) % TX_RING_BUFFER_SIZE;
    }

    for (uint16_t i = 0; i < len; i++) {
        tx_buffer[tx_head] = data[i];
        tx_head = (tx_head + 1) % TX_RING_BUFFER_SIZE;
    }

    return true;
}

/**
 * @brief Processa a fila de transmissão USB.
 *
 * Copia até 64 bytes do buffer circular para um buffer temporário
 * e solicita a transmissão por meio da interface USB CDC.
 *
 * Utiliza um índice temporário de leitura para preservar os dados
 * na fila caso a solicitação de transmissão falhe. O índice oficial
 * de leitura é atualizado somente quando a interface aceita a solicitação.
 *
 * A função retorna imediatamente se a fila estiver vazia ou se já
 * existir uma transmissão em andamento.
 */
void USB_Comm_ProcessTx(void) {
    if (tx_head == tx_tail || is_transmitting) return;

    uint8_t temp_buf[64];
    uint16_t bytes_to_send = 0;

    uint16_t temp_tail = tx_tail;

    while (temp_tail != tx_head && bytes_to_send < 64) {
        temp_buf[bytes_to_send++] = tx_buffer[temp_tail];
        temp_tail = (temp_tail + 1) % TX_RING_BUFFER_SIZE;
    }

    if (bytes_to_send > 0) {
        is_transmitting = true;

        if (CDC_Transmit_HS(temp_buf, bytes_to_send) == USBD_OK) {
            tx_tail = temp_tail;
        } else {
            is_transmitting = false;
        }
    }
}

/**
 * @brief Processa um pacote recebido pela interface USB CDC.
 *
 * Verifica se o tamanho recebido corresponde ao tamanho esperado
 * de um pacote de configuração e se o cabeçalho identifica uma
 * mensagem do tipo HEAD_CONFIG.
 *
 * Quando ambas as verificações são satisfeitas, copia o pacote para
 * a variável interna e sinaliza a disponibilidade de uma nova configuração.
 *
 * @param Buf Ponteiro para o buffer contendo os dados recebidos.
 * @param Len Ponteiro para o tamanho, em bytes, dos dados recebidos.
 */
void USB_Comm_ReceiveCallback(uint8_t *Buf, uint32_t *Len) {
    if (*Len == sizeof(Protocol_ConfigPacket_t)) {
        Protocol_ConfigPacket_t *pkt = (Protocol_ConfigPacket_t *)Buf;

        if (pkt->header == HEAD_CONFIG) {
            memcpy(&rx_config, pkt, sizeof(Protocol_ConfigPacket_t));
            new_config_received = true;
        }
    }
}

/**
 * @brief Notifica a conclusão de uma transmissão USB CDC.
 *
 * Libera a flag de transmissão para permitir o início de um novo envio.
 *
 * Deve ser chamada pelo callback de conclusão da transmissão USB.
 */
void USB_Comm_TxCompleted(void) {
    is_transmitting = false;
}

/**
 * @brief Obtém uma nova configuração recebida pela USB.
 *
 * Se houver uma configuração pendente, copia seus dados para a estrutura
 * fornecida pelo chamador e limpa a flag de disponibilidade.
 *
 * @param config Ponteiro para a estrutura que receberá a configuração.
 *
 * @return true se uma nova configuração foi copiada.
 * @return false se não houver uma nova configuração disponível.
 */
bool USB_Comm_GetNewConfig(Protocol_ConfigPacket_t *config) {
    if (new_config_received) {
        memcpy(config, &rx_config, sizeof(Protocol_ConfigPacket_t));
        new_config_received = false;
        return true;
    }

    return false;
}