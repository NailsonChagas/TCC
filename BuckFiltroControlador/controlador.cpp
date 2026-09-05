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

const double c1 = 0.001906;
const double c2 = 0.00049680633;

extern "C" __declspec(dllexport) void controlador(void **opaque, double t, union uData *data)
{
   double  IN   = data[0].d * (50.0 / 3.3); // ADC input
   bool    CLK  = data[1].b; // input
   bool   &OUT1 = data[2].b; // output -> pwm
   double &OUT2 = data[3].d; // output -> duty cycle

// Implement module evaluation code here:

   // Variaveis do PWM
   static int counter = 0;
   // Define a resolucao do PWM (ex: 1000 passos = incrementos de 0.1%).
   // IMPORTANTE: A frequencia final do PWM depende do sinal de CLK (entrada).
   // Formula: f_pwm = f_clk / counter_max
   // Exemplo prático: Para obter um PWM final de 50 kHz com counter_max = 1000,
   // a fonte de CLK no simulador DEVE estar configurada para 50 MHz (50k * 1000).
   const int counter_max = 100;

   // Variaveis do controlador
   static double Vref = 25.0;
   static double U = 0, pastU = 0.0; // duty
   static double E = 0, pastE = 0.0; // erro

   // Verifica borda de subida (CLK atual é true, estado anterior era false)
   static bool clk_state = false;
   if (CLK == true && clk_state == false) {

      counter++;

      if (counter >= counter_max) {
         counter = 0;

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
