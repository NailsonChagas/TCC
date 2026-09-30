// Automatically generated C++ file on Wed Sep 30 10:48:57 2026
//
// To build with Digital Mars C++ Compiler:
//
//    dmc -mn -WD -o simuladorbuck.cpp kernel32.lib

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
int __stdcall DllMain(void *module, unsigned int reason, void *reserved)
{
    return 1;
}

// #undef pin names lest they collide with names in any header file(s) you might include.
#undef PWM
#undef iL
#undef vC
#undef CLK

// CONFIGURAÇÃO DO DAC
static const float VDAC_MAX = 3.3f;   // Tensão máxima do DAC [V]
static const float VC_MAX   = 50.0f;  // Faixa máxima de tensão da planta [V]
static const float IL_MAX   = 5.0f;   // Faixa máxima de corrente da planta [A]
static const unsigned int DAC_BITS = 18; // Resolução do DAC
static const unsigned int DAC_LEVELS = (1u << DAC_BITS) - 1;


static float quantizeDAC(float voltage)
{
    if (voltage < 0.0f) voltage = 0.0f;
    if (voltage > VDAC_MAX) voltage = VDAC_MAX;

    // Converte tensão para código digital
    float code = voltage * (float)DAC_LEVELS / VDAC_MAX;

    // Arredonda para o código inteiro mais próximo
    unsigned int code_quantized = (unsigned int)(code + 0.5f);

    // Converte novamente o código para tensão
    return ((float)code_quantized * VDAC_MAX) / (float)DAC_LEVELS;
}

extern "C" __declspec(dllexport)
void simuladorbuck(void **opaque, double t, union uData *data)
{
    bool PWM = data[0].b; // Entrada PWM
    bool CLK = data[1].b; // Clock de 550 MHz
    double &iL = data[2].d; // Saída para corrente -> tensão DAC
    double &vC = data[3].d; // Saída para tensão -> tensão DAC

    // VARIÁVEIS DO TEMPORIZADOR
    static unsigned int CLK_counter = 0;
    static bool CLK_pastVal = false;

    // VARIÁVEIS DO DAC
    static float vC_DAC = 0.0f;
    static float iL_DAC = 0.0f;

    // VARIÁVEIS DO MODELO DO BUCK
    static const float Ad_00 = 0.9999265803813119f;
    static const float Ad_01 = -0.00013156940067175223f;
    static const float Ad_10 = 1.0964116722646022f;
    static const float Ad_11 = 0.9736337345236475f;
    static const float Bd1_00_Vs = 0.00666650314952061f;
    static const float Bd1_10_Vs = 0.0036709809344059874f;
    static const float Bd2_00_Vs = 0.0f;
    static const float Bd2_10_Vs = 0.0f;
    static float iL_prev = 0.0f;
    static float vC_prev = 0.0f;
    static float iL_aux = 0.0f;
    static float vC_aux = 0.0f;

    if (CLK && !CLK_pastVal) // DETECÇÃO DA BORDA DE SUBIDA DO CLOCK
    {
        CLK_counter++;

        // EXECUTA O MODELO DO BUCK A 5 MHz
        if (CLK_counter >= 110) // 550 MHz / 5 MHz = 110
        {
            CLK_counter = 0;

            if (PWM) { // PWM = 1 -> Chave fechada
                iL_aux = Ad_00 * iL_prev + Ad_01 * vC_prev + Bd1_00_Vs;
                vC_aux = Ad_10 * iL_prev + Ad_11 * vC_prev + Bd1_10_Vs;
            }
            else { // PWM = 0 -> Chave aberta
                iL_aux = Ad_00 * iL_prev + Ad_01 * vC_prev + Bd2_00_Vs;
                vC_aux = Ad_10 * iL_prev + Ad_11 * vC_prev + Bd2_10_Vs;
            }

            // ATUALIZAÇÃO DOS ESTADOS
            iL_prev = iL_aux;
            vC_prev = vC_aux;

            // CONDICIONAMENTO PARA O DAC
            vC_DAC = vC_aux * VDAC_MAX / VC_MAX;
            iL_DAC = iL_aux * VDAC_MAX / IL_MAX;
            vC_DAC = quantizeDAC(vC_DAC);
            iL_DAC = quantizeDAC(iL_DAC);
        }
    }

    iL = (double)iL_DAC;
    vC = (double)vC_DAC;
    CLK_pastVal = CLK;
}
