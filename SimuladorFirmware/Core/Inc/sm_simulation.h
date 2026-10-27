#ifndef SM_SIMULATION_H 
#define SM_SIMULATION_H

typedef enum {
    AGUARDA_CONFIG,
    CONFIG_SIM,
    EXEC_SIM
} SimState_t;

void SM_Init(void); // Inicializa a máquina de estados
void SM_Process(void); // Processa a máquina de estados, deve ser chamado periodicamente

// Callbacks para os Timers
void SM_Timer_MathStep_ISR(void); // Disparado a f_sim
void SM_Timer_Telemetry_ISR(void); // Disparado a f_s

#endif // SM_SIMULATION_H