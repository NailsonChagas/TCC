// Automatically generated C++ file on Sat Sep  5 13:33:27 2026
//
// To build with Digital Mars C++ Compiler:
//
//    dmc -mn -WD -o controlador.cpp kernel32.lib


union uData
{
   bool b;
   char c;
   unsigned char uc;
   short s;
   unsigned short us;
   int i;
   unsigned int ui;
   float f;
   double d;
   long long int i64;
   unsigned long long int ui64;
   char *str;
   unsigned char *bytes;
};

// int DllMain() must exist and return 1 for a process to load the .DLL
// See https://docs.microsoft.com/en-us/windows/win32/dlls/dllmain for more information.
int __stdcall DllMain(void *module, unsigned int reason, void *reserved) { return 1; }

// #undef pin names lest they collide with names in any header file(s) you might include.
#undef IN
#undef OUT1
#undef OUT2
#undef CLK

// Período de amostragem do controlador (50 kHz = 20 us)
const double Ts = 1.0 / 50000.0; // Importante usar 1.0 para divisão flutuante
const double c1 = 0.001 + (32.5 * Ts);
const double c2 = (32.5 * Ts) - 0.001;

// Configuração do Degrau de Tensão
const double tempo_degrau = 0.003; // Tempo em segundos para o degrau (ex: 0.003 s = 3 ms)
const double Vref_inicial  = 25.0;  // Valor inicial da referência
const double Vref_incremento = 10.0; // Incremento a ser somado no degrau

extern "C" __declspec(dllexport) void controlador(void **opaque, double t, union uData *data)
{
   double   IN   = data[0].d * (50.0 / 3.3); // ADC input
   bool     CLK  = data[1].b; // input
   bool    &OUT1 = data[2].b; // output -> pwm
   double  &OUT2 = data[3].d; // output -> duty cycle

// Implement module evaluation code here:

   // Variaveis do PWM
   static int counter = 0;
   const int counter_max = 10000;

   // Variaveis do controlador
   static double Vref = Vref_inicial;
   static double U = 0, pastU = 0.0; // duty
   static double E = 0, pastE = 0.0; // erro

   // Contador de ciclos do loop de controle
   static int ciclos_controle = 0;
   const int ciclos_limite = (int)(tempo_degrau / Ts); // Calcula quantos ciclos correspondem ao tempo configurado

   // Verifica borda de subida (CLK atual é true, estado anterior era false)
   static bool clk_state = false;
   if (CLK == true && clk_state == false) {

      counter++;

      // Executa a malha do controlador a cada período de amostragem Ts
      if (counter >= counter_max) {
         counter = 0;

         // Lógica do degrau baseada na contagem do clock do micro
         ciclos_controle++;
         if (ciclos_controle >= ciclos_limite) {
            Vref = Vref_inicial + Vref_incremento;
         } else {
            Vref = Vref_inicial;
         }

         E = Vref - IN;
         U = pastU + c1 * E + c2 * pastE;

         if (U > 1.0) { // Saturação do sinal de controle (Duty Cycle entre 0.0 e 1.0)
            U = 1.0;
         } else if (U < 0.0) {
            U = 0.0;
         }

         pastE = E;
         pastU = U;
      }

      if ((U * counter_max) > counter) {
         OUT1 = 1;
      }
      else {
         OUT1 = 0;
      }

      OUT2 = U; // sempre atualizar a saida com U para poder mostrar o duty no grafico
   }

   // Sempre atualiza o estado do clock para a próxima iteração
   clk_state = CLK;
}
