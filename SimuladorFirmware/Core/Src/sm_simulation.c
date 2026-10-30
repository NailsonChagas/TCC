#include "sm_simulation.h"
#include "comm_protocol.h"
#include "usb_comm.h"
#include "main.h"

extern TIM_HandleTypeDef htim1;
extern TIM_HandleTypeDef htim2;
extern DAC_HandleTypeDef hdac1;

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
 * O TIM1 opera na frequência de simulação, responsável pela
 * atualização dos estados do modelo discreto. O TIM2 opera na
 * frequência definida para a atualização da saída analógica e
 * o envio da telemetria.
 *
 * O cálculo pressupõe prescaler igual a zero e utiliza
 * SystemCoreClock como frequência de entrada dos temporizadores.
 */
static void __config_hardware_freqs(void) {
    uint32_t pclk1 = HAL_RCC_GetPCLK1Freq(); // Barramento do TIM2 (APB1)
    uint32_t pclk2 = HAL_RCC_GetPCLK2Freq(); // Barramento do TIM1 (APB2)
    uint32_t tim2_clock = pclk1 * 2; // TIM2 está no APB1, que tem um multiplicador de 2
    uint32_t tim1_clock = pclk2 * 2; // TIM1 está no APB2, que tem um multiplicador de 2

    float fs = cfg.fs;
    uint32_t n = cfg.n;
    float f_sim = fs * (float)n;

    uint32_t arr_sim = (uint32_t)(tim1_clock / f_sim) - 1;
    uint32_t arr_fs  = (uint32_t)(tim2_clock / ((fs * 2) + 1)) - 1;

    __HAL_TIM_SET_AUTORELOAD(&htim1, arr_sim);
    __HAL_TIM_SET_AUTORELOAD(&htim2, arr_fs);

    __HAL_TIM_SET_COUNTER(&htim1, 0);
    __HAL_TIM_SET_COUNTER(&htim2, 0);  
}


/**
 * @brief Interrompe os periféricos utilizados na simulação.
 *
 * Desabilita as interrupções dos temporizadores e desativa o canal
 * do DAC utilizado para representar a tensão do capacitor.
 */
static void __stop_sim_hardware(void) {
    HAL_TIM_Base_Stop_IT(&htim1);
    HAL_TIM_Base_Stop_IT(&htim2);
    HAL_DAC_Stop(&hdac1, DAC_CHANNEL_1);
}

/**
 * @brief Inicializa os periféricos necessários para a simulação.
 *
 * Habilita o canal do DAC para permitir a atualização da saída
 * analógica por meio de escritas diretas no registrador de dados,
 * realizadas pela função HAL_DAC_SetValue().
 *
 * Inicia o TIM2, responsável pela atualização da saída analógica
 * e pelo envio da telemetria, e o TIM1, responsável pelos cálculos
 * do modelo discreto do conversor.
 *
 * A transferência de dados para o DAC é realizada pela CPU,
 * sem utilização de DMA.
 */
static void __start_sim_hardware(void) {
    HAL_DAC_Start(&hdac1, DAC_CHANNEL_1);
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
 * configura os temporizadores e os estados iniciais do modelo.
 * No estado EXEC_SIM, verifica se o número de passos configurado
 * foi atingido.
 *
 * Os cálculos do modelo são executados na interrupção do TIM1.
 * A atualização da saída analógica é realizada por escrita direta
 * no DAC durante a execução do passo do modelo.
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
 * A contribuição dos coeficientes de entrada é determinada pelo
 * estado lógico da chave, lido diretamente do pino PA0.
 *
 * Após atualizar os estados do modelo, converte a tensão do
 * capacitor para um código digital de 12 bits e escreve o valor
 * diretamente no DAC por meio de HAL_DAC_SetValue(), sem DMA.
 *
 * Deve ser chamada pela interrupção do temporizador configurado
 * para operar na frequência de simulação.
 */
void SM_Timer_MathStep_ISR(void) {
    if (current_state != EXEC_SIM || k >= cfg.total_steps) return;

    // Calcula a parcela constante da equação (que não depende do PWM)
    float new_iL = (cfg.Ad_00 * iL_val) + (cfg.Ad_01 * vC_val);
    float new_vC = (cfg.Ad_10 * iL_val) + (cfg.Ad_11 * vC_val);

    // Avalia o estado físico da chave (pino PA0)
    if ((GPIOA->IDR & GPIO_PIN_0) != 0) {
        // Chave fechada (1): soma os coeficientes de entrada
        new_iL += cfg.Bd1_0;
        new_vC += cfg.Bd1_1;
    }

    // Atualiza os estados
    iL_val = new_iL;
    vC_val = new_vC;

    // Converte a tensão calculada para o DAC (0 a 4095)
    float dac_float = (vC_val / cfg.vO_max) * 4095.0f;

    // Saturação (Clamp) para evitar overflow no DAC
    if (dac_float < 0.0f) dac_float = 0.0f;
    else if (dac_float > 4095.0f) dac_float = 4095.0f;

    // Atualiza diretamente o registrador de dados do DAC
    HAL_DAC_SetValue(&hdac1, DAC_CHANNEL_1, DAC_ALIGN_12B_R, (uint32_t)dac_float);
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