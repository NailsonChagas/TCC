import numpy as np

from models.BuckConverterCCM import BuckConverterCCM
from utils.constants import FSIM, SINE_TABLE_SIZE


class SimulatorTest:
    """
    Representa um cenário de teste para simulação de um conversor Buck em CCM.

    A classe define as condições de entrada do conversor, permitindo aplicar
    uma perturbação senoidal sobre a tensão contínua de alimentação.

    A tensão de entrada é definida pela expressão:

        Vin(t) = Vs + A * sin(2πft)

    onde:

        Vs : tensão contínua de entrada do conversor (V);
        A  : amplitude da perturbação senoidal (V);
        f  : frequência da perturbação senoidal (Hz).

    A implementação utiliza uma tabela de seno discretizada, semelhante à
    abordagem utilizada em sistemas embarcados. A tabela contém valores
    normalizados em formato inteiro de 16 bits (int16), variando entre
    -32767 e +32767.

    A reconstrução do sinal senoidal é realizada através da relação:

        Vin = Vs + amplitude * value / 32767.0

    onde `value` corresponde ao valor atual obtido da tabela de seno.

    Attributes
    ----------
    converter : BuckConverterCCM
        Conversor Buck utilizado como planta do teste.

    Vs : float
        Tensão contínua de entrada do conversor em volts.

    Vs_amplitude : float
        Amplitude da perturbação senoidal aplicada sobre a tensão de entrada
        em volts.

    Vs_frequency : float
        Frequência da perturbação senoidal aplicada sobre a tensão de entrada
        em hertz.

    sine_table : numpy.ndarray
        Tabela contendo uma representação discreta de um ciclo completo da
        função seno. Os valores são armazenados como inteiros de 16 bits
        (`int16`) no intervalo [-32767, 32767].

    phase_increment : float
        Incremento de fase utilizado para percorrer a tabela de seno a cada
        passo da simulação.

        O valor é calculado por:

            phase_increment = (f * N) / FSIM

        onde:

            f    : frequência desejada do sinal senoidal;
            N    : quantidade de amostras da tabela de seno;
            FSIM : frequência de simulação.

        Esse valor representa quantas posições da tabela devem ser avançadas
        a cada passo de simulação para gerar a frequência desejada.
    """

    # Tabela de seno normalizada convertida para int16.
    #
    # A tabela representa um período completo da função seno:
    #
    #       sin(0) até sin(2π)
    #
    # Os valores são escalados para utilizar a faixa disponível de um inteiro
    # com sinal de 16 bits:
    #
    #       -32767 <= valor <= +32767
    #
    # Essa representação permite utilizar menos sram no microcontrolador
    
    sine_table = (
        np.sin(
            np.linspace(
                0,
                2 * np.pi,
                SINE_TABLE_SIZE,
                endpoint=False,
            )
        ) * 32767
    ).astype(np.int16)

    def __init__(
        self,
        converter: BuckConverterCCM,
        amplitude: float,
        frequency: float,
    ) -> None:
        """
        Inicializa um cenário de teste do conversor.

        Parameters
        ----------
        converter : BuckConverterCCM
            Instância do conversor Buck que será utilizado na simulação.

        amplitude : float
            Amplitude da perturbação senoidal aplicada à tensão de entrada (V).

        frequency : float
            Frequência da perturbação senoidal aplicada à tensão de entrada (Hz).
        """

        self.converter = converter

        # Tensão DC de entrada do conversor
        self.Vs = converter.Vs

        # Características da perturbação senoidal aplicada na entrada
        self.Vs_amplitude = amplitude
        self.Vs_frequency = frequency

        # Quantidade de posições da tabela de seno avançadas a cada passo
        # de simulação para gerar a frequência configurada.
        #
        # Exemplo:
        # FSIM = 200 kHz
        # SINE_TABLE_SIZE = 1024
        # f = 100 Hz
        #
        # phase_increment = (100 * 1024) / 200000
        # phase_increment = 0.512 posições por passo
        #
        # Como o incremento pode ser fracionário, a implementação do STM32
        # deve utilizar um acumulador de fase para controlar a posição da tabela.
        self.phase_increment = (self.Vs_frequency * SINE_TABLE_SIZE) / FSIM

    def __repr__(self) -> str:
        return (
            "SimulatorTest("
            f"converter={self.converter}, "
            f"Vs={self.Vs}, "
            f"Vs_amplitude={self.Vs_amplitude}, "
            f"Vs_frequency={self.Vs_frequency}, "
            f"phase_increment={self.phase_increment}"
            ")"
        )