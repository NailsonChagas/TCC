#include "sm_simulation.h"
#include "comm_protocol.h"

// Variaveis da maquina de estados
static volatile SimState_t current_state = AGUARDA_CONFIG;
static Protocol_ConfigPacket_t cfg;

// Variaveis da simulacao
static volatile uint32_t k = 0;
static volatile float iL_val = 0.0f;
static volatile float vC_val = 0.0f;

void SM_Init(void) {
    current_state = AGUARDA_CONFIG;
    k = 0;
}

void SM_Process(void) {
    switch(current_state) {
        case AGUARDA_CONFIG:
            // Aguarda a recepção do pacote de configuração
            // Se o pacote for recebido e válido, passa para o estado CONFIG_SIM
            break;

        case CONFIG_SIM:
            // Configura a simulação com os parâmetros recebidos
            // Inicializa variáveis e prepara para a execução
            current_state = EXEC_SIM;
            break;

        case EXEC_SIM:
            // Executa a simulação passo a passo
            // Atualiza iL_val e vC_val com base na lógica da simulação
            // Incrementa k até atingir total_steps
            if (k >= cfg.total_steps) {
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
    if (current_state != EXEC_SIM) return;
}

void SM_Timer_Telemetry_ISR(void) {
    if (current_state != EXEC_SIM) return;
}
