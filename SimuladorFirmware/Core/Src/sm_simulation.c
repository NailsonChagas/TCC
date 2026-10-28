#include "sm_simulation.h"
#include "comm_protocol.h"
#include "usb_comm.h"
#include "main.h" // Acesso aos handles (htim1, hdac1, etc)

// Handles gerados pelo CubeMX
extern TIM_HandleTypeDef htim1;
extern TIM_HandleTypeDef htim2;
extern DAC_HandleTypeDef hdac1;

// --- Buffers de DMA ---
volatile uint16_t dma_dac_buffer = 0;
static volatile bool switch_state = false;

// Variaveis da maquina de estados
static volatile SimState_t current_state = AGUARDA_CONFIG;
static Protocol_ConfigPacket_t cfg;

// Variaveis da simulacao
static volatile uint32_t k = 0;
static volatile float iL_val = 0.0f;
static volatile float vC_val = 0.0f;

static void __config_hardware_freqs(void) {
    // Obtém o clock base dos timers. No H7, os timers costumam 
    // rodar no clock máximo do sistema ou metade dele (ex: 275 MHz ou 550 MHz).
    // Modifique SystemCoreClock caso seus timers estejam em um barramento mais lento.
    uint32_t timer_clock = SystemCoreClock; // Frequência do barramento do Timer (Hz)
    
    float fs = cfg.fs;
    uint32_t n = cfg.n;
    float f_sim = fs * (float)n;

    // Calcula os valores para o Auto Reload Register (ARR) assumindo Prescaler = 0
    uint32_t arr_sim = (uint32_t)(timer_clock / f_sim) - 1;
    uint32_t arr_fs  = (uint32_t)(timer_clock / fs) - 1;

    __HAL_TIM_SET_AUTORELOAD(&htim1, arr_sim); // f_sim
    __HAL_TIM_SET_AUTORELOAD(&htim2, arr_fs);  // fs (DAC e Telemetria)
    
    // Zera os contadores para iniciar de forma síncrona
    __HAL_TIM_SET_COUNTER(&htim1, 0);
    __HAL_TIM_SET_COUNTER(&htim2, 0);
}

static void __stop_sim_hardware(void) {
    HAL_TIM_Base_Stop_IT(&htim1);
    HAL_TIM_Base_Stop_IT(&htim2);
    HAL_DAC_Stop_DMA(&hdac1, DAC_CHANNEL_1);
}

static void __start_sim_hardware(void) {
    // 1. Inicia DMA do DAC e seu Timer gatilho
    HAL_DAC_Start_DMA(&hdac1, DAC_CHANNEL_1, (uint32_t*)&dma_dac_buffer, 1, DAC_ALIGN_12B_R);
    HAL_TIM_Base_Start_IT(&htim2); // Telemetria e Trigger do DAC a fs
    // 2. Inicia o timer da matemática
    HAL_TIM_Base_Start_IT(&htim1); // Matemática a f_sim
}

static void __send_header_only(uint16_t header) {
    uint16_t pkt = header;
    USB_Comm_QueueTxData((uint8_t*)&pkt, sizeof(uint16_t));
}

void SM_Init(void) {
    current_state = AGUARDA_CONFIG;
}

void SM_Process(void) {
    switch(current_state) {
        case AGUARDA_CONFIG:
            // Aguarda a recepção do pacote de configuração
            // Se o pacote for recebido e válido, passa para o estado CONFIG_SIM
            if (USB_Comm_GetNewConfig(&cfg)) {
                __stop_sim_hardware(); // garantido que n tem interrupção dos timers
                current_state = CONFIG_SIM;
            }
            break;

        case CONFIG_SIM:
            // Configura a simulação com os parâmetros recebidos
            // Inicializa variáveis e prepara para a execução
            if (cfg.fs > 0.0f && cfg.n > 0 && cfg.total_steps > 0) {
                __config_hardware_freqs();

                // Inicializa variáveis e prepara para a execução
                k = 0;
                iL_val = 0.0f;
                vC_val = 0.0f;
                dma_dac_buffer = 0;
                switch_state = false;
                
                // Envia a confirmação para o computador
                __send_header_only(HEAD_CONFIG_SUCCESS);
                current_state = EXEC_SIM;
                __start_sim_hardware();
            } else {
                // Se os parâmetros forem inválidos, avisa o PC e reseta
                __send_header_only(HEAD_CONFIG_FAIL);
                current_state = AGUARDA_CONFIG;
            }
            break;

        case EXEC_SIM:
            // Executa a simulação passo a passo
            // Atualiza iL_val e vC_val com base na lógica da simulação
            // Incrementa k até atingir total_steps
            if (k >= cfg.total_steps) {
                __stop_sim_hardware();
                __send_header_only(HEAD_SIM_END);
                current_state = AGUARDA_CONFIG; // Retorna ao estado inicial após a simulação
            }
            break;

        default:
            // Estado inválido, retorna ao estado inicial
            current_state = AGUARDA_CONFIG;
            break;
    }
}

void SM_Timer_MathStep_ISR(void) {
    if (current_state != EXEC_SIM || k >= cfg.total_steps) return;

    switch_state = (GPIOA->IDR & GPIO_PIN_0) != 0; // vai ver se o PWM do controlador esta em HIGH ou LOW

    // logica da simulação vai vir aqui

    k++;
}

void SM_Timer_Telemetry_ISR(void) {
    if (current_state != EXEC_SIM) return;
    Protocol_DataPacket_t data;
    data.header = HEAD_DATA;
    data.k = k;           // Envia o k atualizado pela interrupção matemática
    data.iL = 0.0f;       // Força 0 
    data.vC_val = 0.0f;   // Força 0 
    USB_Comm_QueueTxData((uint8_t*)&data, sizeof(Protocol_DataPacket_t));
}
