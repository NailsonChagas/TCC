#include "sm_simulation.h"
#include "comm_protocol.h"
#include "usb_comm.h"
#include "main.h"

extern TIM_HandleTypeDef htim1;
extern TIM_HandleTypeDef htim2;
extern DAC_HandleTypeDef hdac1;

/**
 * @brief Buffer utilizado pelo DMA para atualizar a saída do DAC.
 */
volatile uint16_t dma_dac_buffer = 0;

/**
 * @brief Estado lógico da chave do conversor Buck.
 *
 * Utilizado como fator multiplicativo dos coeficientes de entrada
 * do modelo discreto.
 */
static volatile float switch_state = 0.0f;

/**
 * @brief Estado atual da máquina de estados da simulação.
 */
static volatile SimState_t current_state = AGUARDA_CONFIG;

/**
 * @brief Parâmetros recebidos para a configuração da simulação.
 */
static Protocol_ConfigPacket_t cfg;

/**
 * @brief Índice do passo atual da simulação.
 */
static volatile uint32_t k = 0;

/**
 * @brief Corrente no indutor calculada pelo modelo, em ampères.
 */
static volatile float iL_val = 0.0f;

/**
 * @brief Tensão no capacitor calculada pelo modelo, em volts.
 */
static volatile float vC_val = 0.0f;

/**
 * @brief Configura as frequências de operação dos temporizadores.
 *
 * Calcula os valores de recarga dos temporizadores com base na
 * frequência de chaveamento e no fator de sobreamostragem.
 *
 * O TIM1 opera na frequência de simulação, enquanto o TIM2 opera
 * na frequência de chaveamento, utilizada para a atualização do
 * DAC e o envio da telemetria.
 *
 * O cálculo pressupõe prescaler igual a zero e utiliza
 * SystemCoreClock como frequência de entrada dos temporizadores.
 */
static void __config_hardware_freqs(void) {
    uint32_t timer_clock = SystemCoreClock;

    float fs = cfg.fs;
    uint32_t n = cfg.n;
    float f_sim = fs * (float)n;

    uint32_t arr_sim = (uint32_t)(timer_clock / f_sim) - 1;
    uint32_t arr_fs  = (uint32_t)(timer_clock / fs) - 1;

    __HAL_TIM_SET_AUTORELOAD(&htim1, arr_sim);
    __HAL_TIM_SET_AUTORELOAD(&htim2, arr_fs);

    __HAL_TIM_SET_COUNTER(&htim1, 0);
    __HAL_TIM_SET_COUNTER(&htim2, 0);
}

/**
 * @brief Interrompe os periféricos utilizados na simulação.
 *
 * Desabilita as interrupções dos temporizadores e interrompe
 * a transferência de dados para o DAC via DMA.
 */
static void __stop_sim_hardware(void) {
    HAL_TIM_Base_Stop_IT(&htim1);
    HAL_TIM_Base_Stop_IT(&htim2);
    HAL_DAC_Stop_DMA(&hdac1, DAC_CHANNEL_1);
}

/**
 * @brief Inicializa os periféricos necessários para a simulação.
 *
 * Inicia a transferência via DMA para o DAC, habilita o temporizador
 * responsável pela telemetria e pela atualização do DAC e inicia
 * o temporizador responsável pelos cálculos do modelo.
 */
static void __start_sim_hardware(void) {
    HAL_DAC_Start_DMA(&hdac1, DAC_CHANNEL_1, (uint32_t*)&dma_dac_buffer, 1, DAC_ALIGN_12B_R);
    HAL_TIM_Base_Start_IT(&htim2);
    HAL_TIM_Base_Start_IT(&htim1);
}

/**
 * @brief Envia um cabeçalho de protocolo sem dados adicionais.
 *
 * Insere o cabeçalho informado na fila de transmissão USB.
 *
 * @param header Identificador do pacote a ser transmitido.
 */
static void __send_header_only(uint16_t header) {
    uint16_t pkt = header;
    USB_Comm_QueueTxData((uint8_t*)&pkt, sizeof(uint16_t));
}

/**
 * @brief Inicializa a máquina de estados da simulação.
 *
 * Define o estado inicial como AGUARDA_CONFIG.
 */
void SM_Init(void) {
    current_state = AGUARDA_CONFIG;
}

/**
 * @brief Processa as transições da máquina de estados.
 *
 * No estado AGUARDA_CONFIG, aguarda o recebimento dos parâmetros
 * de configuração. No estado CONFIG_SIM, valida os parâmetros e
 * configura os periféricos. No estado EXEC_SIM, verifica se o
 * número de passos configurado foi atingido.
 *
 * Os cálculos do modelo são executados na interrupção do temporizador
 * dedicado à atualização dos estados do conversor.
 */
void SM_Process(void) {
    switch(current_state) {
        case AGUARDA_CONFIG:
            if (USB_Comm_GetNewConfig(&cfg)) {
                __stop_sim_hardware();
                current_state = CONFIG_SIM;
            }
            break;

        case CONFIG_SIM:
            if (cfg.fs > 0.0f && cfg.n > 0 && cfg.total_steps > 0) {
                __config_hardware_freqs();

                k = 0;
                iL_val = 0.0f;
                vC_val = 0.0f;
                dma_dac_buffer = 0;
                switch_state = 0.0f;

                __send_header_only(HEAD_CONFIG_SUCCESS);
                current_state = EXEC_SIM;
                __start_sim_hardware();
            } else {
                __send_header_only(HEAD_CONFIG_FAIL);
                current_state = AGUARDA_CONFIG;
            }
            break;

        case EXEC_SIM:
            if (k >= cfg.total_steps) {
                __stop_sim_hardware();
                __send_header_only(HEAD_SIM_END);
                current_state = AGUARDA_CONFIG;
            }
            break;

        default:
            current_state = AGUARDA_CONFIG;
            break;
    }
}

/**
 * @brief Executa um passo do modelo discreto do conversor Buck.
 *
 * Atualiza a corrente no indutor e a tensão no capacitor utilizando
 * as equações de estado discretizadas recebidas na configuração.
 *
 * Converte a tensão do capacitor para uma representação digital
 * de 12 bits e atualiza o buffer utilizado pelo DMA do DAC.
 *
 * Deve ser chamada pela interrupção do temporizador configurado
 * para operar na frequência de simulação.
 */
void SM_Timer_MathStep_ISR(void) {
    if (current_state != EXEC_SIM || k >= cfg.total_steps) return;

    // switch_state = 1.0f para testar com PWM sempre ligado
    switch_state = 1.0f; // ((GPIOA->IDR & GPIO_PIN_0) != 0) ? 1.0f : 0.0f; 

    float new_iL = (cfg.Ad_00 * iL_val) + (cfg.Ad_01 * vC_val) + (cfg.Bd1_0 * switch_state);
    float new_vC = (cfg.Ad_10 * iL_val) + (cfg.Ad_11 * vC_val) + (cfg.Bd1_1 * switch_state);

    iL_val = new_iL;
    vC_val = new_vC;

    float dac_float = (vC_val / cfg.vO_max) * 4095.0f;

    if (dac_float < 0.0f) dac_float = 0.0f;
    else if (dac_float > 4095.0f) dac_float = 4095.0f;

    dma_dac_buffer = (uint16_t)dac_float;

    k++;
}

/**
 * @brief Prepara e enfileira um pacote de telemetria.
 *
 * Registra o índice do passo atual, a corrente no indutor e a
 * tensão no capacitor. O pacote é inserido na fila de transmissão
 * USB para envio assíncrono, sem aguardar a conclusão da transmissão.
 *
 * Deve ser chamada pela interrupção do temporizador responsável
 * pela telemetria.
 */
void SM_Timer_Telemetry_ISR(void) {
    if (current_state != EXEC_SIM) return;

    Protocol_DataPacket_t data;
    data.header = HEAD_DATA;
    data.k = k;
    data.iL = iL_val;
    data.vC_val = vC_val;

    USB_Comm_QueueTxData((uint8_t*)&data, sizeof(Protocol_DataPacket_t));
}
