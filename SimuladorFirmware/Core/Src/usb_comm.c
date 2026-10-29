#include "usb_comm.h"
#include "usbd_cdc_if.h"
#include <string.h>

/**
 * @brief Buffer circular para armazenamento dos dados pendentes de transmissão USB.
 */
static uint8_t tx_buffer[TX_RING_BUFFER_SIZE];

/**
 * @brief Índice de inserção no buffer circular.
 *
 * Indica a próxima posição disponível para escrita.
 */
static volatile uint16_t tx_head = 0;

/**
 * @brief Índice de leitura do buffer circular.
 *
 * Indica o próximo byte pendente de transmissão.
 */
static volatile uint16_t tx_tail = 0;

/**
 * @brief Indica se existe uma transmissão USB em andamento.
 */
static volatile bool is_transmitting = false;

/**
 * @brief Buffer estático temporário para transmissão USB.
 *
 * Diferentemente da versão anterior, em que o buffer temporário era
 * alocado na pilha de USB_Comm_ProcessTx(), este buffer possui duração
 * estática, permanecendo válido após o retorno da função enquanto
 * a transmissão USB assíncrona estiver em andamento.
 */
static uint8_t temp_buf[64];

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
 * seja insuficiente, descarta dados antigos antes de inserir o novo bloco.
 *
 * A manipulação dos índices e a inserção dos dados são protegidas por
 * uma seção crítica. As interrupções são temporariamente desabilitadas
 * para impedir que uma rotina executada por interrupção acesse ou altere
 * os índices durante a operação, evitando condições de corrida e
 * inconsistências no gerenciamento do buffer circular.
 *
 * Em relação à versão anterior, foram introduzidas as seguintes alterações:
 * - Rejeição explícita de inserções com tamanho zero.
 * - Proteção da manipulação dos índices e da inserção dos dados por
 *   uma seção crítica, preservando o estado anterior das interrupções.
 * - Descarte calculado em múltiplos do tamanho do novo bloco, em vez
 *   do descarte da quantidade mínima de bytes necessária.
 * - Remoção da chamada antecipada de USB_Comm_ProcessTx(), separando
 *   a inserção dos dados do processamento da transmissão.
 *
 * O descarte em múltiplos do tamanho do bloco pressupõe alinhamento
 * entre o índice de leitura e os limites dos pacotes. Essa condição
 * não é garantida apenas pelo cálculo implementado.
 *
 * @param data Ponteiro para os dados que serão enfileirados.
 * @param len Quantidade de bytes a serem inseridos.
 *
 * @return true se os dados forem aceitos pela fila.
 * @return false se o tamanho for zero ou maior ou igual à capacidade
 *         total do buffer circular.
 */
bool USB_Comm_QueueTxData(const uint8_t *data, uint16_t len) {
    if (len >= TX_RING_BUFFER_SIZE || len == 0) return false;

    uint32_t primask = __get_PRIMASK();
    __disable_irq();

    uint16_t free_space = (tx_tail <= tx_head) ?
                          (TX_RING_BUFFER_SIZE - tx_head + tx_tail - 1) :
                          (tx_tail - tx_head - 1);

    if (len > free_space) {
        uint16_t bytes_needed = len - free_space;
        uint16_t packets_to_drop = (bytes_needed + len - 1) / len;
        uint16_t bytes_to_discard = packets_to_drop * len;

        /* Descarta em múltiplos do tamanho do bloco recebido. */
        tx_tail = (tx_tail + bytes_to_discard) % TX_RING_BUFFER_SIZE;
    }

    for (uint16_t i = 0; i < len; i++) {
        tx_buffer[tx_head] = data[i];
        tx_head = (tx_head + 1) % TX_RING_BUFFER_SIZE;
    }

    __set_PRIMASK(primask);
    return true;
}

/**
 * @brief Processa a fila de transmissão USB.
 *
 * Copia até 64 bytes do buffer circular para o buffer temporário
 * estático e solicita a transmissão por meio da interface USB CDC.
 *
 * A verificação da fila, a cópia dos dados e a atualização da flag
 * de transmissão são protegidas por uma seção crítica. As interrupções
 * são temporariamente desabilitadas para impedir que outra rotina
 * altere os índices durante a cópia, garantindo a consistência dos
 * dados preparados para transmissão e evitando solicitações concorrentes.
 *
 * Em relação à versão anterior, o buffer temporário deixou de ser
 * alocado na pilha e passou a ser estático, garantindo que sua memória
 * permaneça válida durante a transmissão assíncrona.
 *
 * O índice de leitura é atualizado somente quando a interface USB
 * aceita a solicitação de transmissão. Caso a solicitação falhe,
 * os dados permanecem pendentes na fila.
 *
 * A chamada antecipada desta função foi removida de
 * USB_Comm_QueueTxData(). Portanto, o processamento da fila deve
 * ser acionado pelo fluxo principal do firmware.
 */
void USB_Comm_ProcessTx(void) {
    if (is_transmitting) return;

    uint16_t bytes_to_send = 0;

    uint32_t primask = __get_PRIMASK();
    __disable_irq();

    if (tx_head == tx_tail) {
        __set_PRIMASK(primask);
        return;
    }

    uint16_t temp_tail = tx_tail;
    while (temp_tail != tx_head && bytes_to_send < 64) {
        temp_buf[bytes_to_send++] = tx_buffer[temp_tail];
        temp_tail = (temp_tail + 1) % TX_RING_BUFFER_SIZE;
    }

    is_transmitting = true;
    __set_PRIMASK(primask);

    if (CDC_Transmit_HS(temp_buf, bytes_to_send) == USBD_OK) {
        uint32_t primask_tx = __get_PRIMASK();
        __disable_irq();
        tx_tail = temp_tail;
        __set_PRIMASK(primask_tx);
    } else {
        is_transmitting = false;
    }
}

/**
 * @brief Processa um pacote recebido pela interface USB CDC.
 *
 * Verifica se o tamanho recebido corresponde ao tamanho esperado
 * de um pacote de configuração e se o cabeçalho identifica uma
 * mensagem do tipo HEAD_CONFIG.
 *
 * Quando ambas as condições são satisfeitas, copia o pacote para
 * a estrutura interna e sinaliza a disponibilidade de uma nova
 * configuração.
 *
 * Esta função mantém o mesmo comportamento da versão anterior.
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
 * Esta função mantém o mesmo comportamento da versão anterior.
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
 * Esta função mantém o mesmo comportamento da versão anterior.
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