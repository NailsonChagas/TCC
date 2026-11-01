
// Automatically generated C++ file

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

int __stdcall DllMain(void *module, unsigned int reason, void *reserved) { return 1; }

#undef IN
#undef OUT1
#undef OUT2
#undef CLK

// Periodo de amostragem: 50 kHz
const double Ts = 1.0 / 50000.0;
const double c1 = 0.001 + (32.5 * Ts);
const double c2 = (32.5 * Ts) - 0.001;

// Temporizacao
const double tempo_ligamento = 1.0734520;  // 1073.4520 ms
const double tempo_degrau = 30.2689620;    // 30268.9620 ms

// Referencias
const double Vref_inicial = 25.0;
const double Vref_final = 35.0;

extern "C" __declspec(dllexport) void controlador(void **opaque, double t, union uData *data)
{
   double IN = data[0].d * (50.0 / 3.3);
   bool CLK = data[1].b;
   bool &OUT1 = data[2].b;
   double &OUT2 = data[3].d;

   // PWM
   static int counter = 0;
   const int counter_max = 10000;

   // Controlador PI
   static double Vref = Vref_inicial;
   static double U = 0.0;
   static double pastU = 0.0;
   static double E = 0.0;
   static double pastE = 0.0;

   // Estado anterior do clock
   static bool clk_state = false;

   if (CLK == true && clk_state == false) {

      counter++;

      // Controlador habilitado somente a partir de 1073 ms
      if (t >= tempo_ligamento) {

         if (counter >= counter_max) {
            counter = 0;

            // Alteracao da referencia em 30269 ms
            if (t >= tempo_degrau) {
               Vref = Vref_final;
            } else {
               Vref = Vref_inicial;
            }

            E = Vref - IN;
            U = pastU + c1 * E + c2 * pastE;

            // Saturacao do duty cycle
            if (U > 1.0) {
               U = 1.0;
            } else if (U < 0.0) {
               U = 0.0;
            }

            pastE = E;
            pastU = U;
         }

         // Geracao do PWM
         if ((U * counter_max) > counter) {
            OUT1 = 1;
         } else {
            OUT1 = 0;
         }

         OUT2 = U;

      } else {

         // Controlador desabilitado
         counter = 0;
         U = 0.0;
         pastU = 0.0;
         E = 0.0;
         pastE = 0.0;

         OUT1 = 0;
         OUT2 = 0.0;
      }
   }

   clk_state = CLK;
}
