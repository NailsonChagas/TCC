import numpy as np
from scipy.linalg import expm

FS = 5e3


class CCMError(ValueError):
    """Exceção lançada quando o conversor não opera em CCM."""


class BuckConverterCCM:
    def __init__(self, Vs: float, Vo: float, R: float, L: float, C: float, fs: float = FS) -> None:
        self.Vs = Vs
        self.Vo = Vo
        self.R = R
        self.L = L
        self.C = C
        self.fs = fs

        if self.L <= self.Lmin:
            raise CCMError(
                f"O conversor não opera em CCM "
                f"(L={self.L:.6e} H <= Lmin={self.Lmin:.6e} H)."
            )

    @classmethod
    def from_design_parameters(
        cls, Vs: float, Vo: float, Po: float, delta_iL: float, delta_Vo: float, fs: float = FS,
    ) -> "BuckConverterCCM":

        R = Vo**2 / Po
        D = Vo / Vs

        L = Vo * (1 - D) / (delta_iL * fs)

        C = Vo * (1 - D) / (
            8 * L * delta_Vo * fs**2
        )

        return cls(
            Vs=Vs,
            Vo=Vo,
            R=R,
            L=L,
            C=C,
            fs=fs,
        )

    @classmethod
    def from_circuit_components(
        cls,
        Vs: float,
        Vo: float,
        R: float,
        L: float,
        C: float,
        fs: float = FS,
    ) -> "BuckConverterCCM":
        """
        Cria um conversor Buck em CCM a partir dos componentes do circuito.

        Este método deve ser utilizado quando os valores da resistência de
        carga, indutância e capacitância já são conhecidos.

        Args:
            Vs: Tensão de entrada (V).
            Vo: Tensão de saída (V).
            R: Resistência da carga (Ω).
            L: Indutância (H).
            C: Capacitância (F).
            fs: Frequência de chaveamento (Hz).

        Returns:
            Uma instância de ``BuckConverterCCM``.

        Raises:
            CCMError: Se a indutância informada não satisfizer a condição de
                operação em modo de condução contínua (CCM).
        """
        return cls(Vs, Vo, R, L, C, fs)

    @property
    def D(self) -> float:
        """Razão cíclica nominal."""
        return self.Vo / self.Vs

    @property
    def Lmin(self) -> float:
        """Indutância mínima para operação em CCM."""
        return (1 - self.D) * self.R / (2 * self.fs)

    def discretize_model(self, N: int, sim_time: float) -> tuple[float, float, float, float, float, float, float, int]:
        """
        Discretiza o modelo em espaço de estados usando ZOH.

        Retorna
        -------
        Ad_00, Ad_01, Bd1_0, Ad_10, Ad_11, Bd1_1 : float
            Elementos escalares das matrizes discretas Ad e Bd1.

        total_steps : int
            Número total de pontos de simulação.
        """
        fs_sim = self.fs * N

        T_s = 1.0 / self.fs
        timestep = T_s / N
        total_steps = int(round(sim_time / timestep))

        # Modelo contínuo
        A = np.array([
            [0.0, -1.0 / self.L],
            [1.0 / self.C, -1.0 / (self.R * self.C)],
        ])
        B1 = np.array([1.0 / self.L, 0.0])

        # Discretização ZOH
        Ad = expm(A * timestep)
        A_inv = np.linalg.inv(A)
        Bd1 = A_inv @ (Ad - np.eye(2)) @ B1

        return (
            float(Ad[0, 0]),
            float(Ad[0, 1]),
            float(Bd1[0]) * self.Vs,
            float(Ad[1, 0]),
            float(Ad[1, 1]),
            float(Bd1[1]) * self.Vs,
            fs_sim,
            total_steps,
        )

    def simulate(self, N: int, sim_time: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Executa a simulação temporal do conversor Buck.

        Parâmetros
        ----------
        N : int
            Fator de sobreamostragem da simulação:
            fs_sim = N * fs.

        sim_time : float
            Tempo total de simulação [s].

        Retorna
        -------
        time : np.ndarray
            Vetor de tempo [s].

        iL : np.ndarray
            Corrente no indutor [A].

        vC : np.ndarray
            Tensão no capacitor [V].
        """
        # Obtenção dos coeficientes discretizados
        (
            Ad_00,
            Ad_01,
            Bd1_0,
            Ad_10,
            Ad_11,
            Bd1_1,
            fs_sim,
            total_steps,
        ) = self.discretize_model(N, sim_time)

        T_s = 1.0 / self.fs

        # Vetores de saída
        time = np.linspace(0, sim_time, total_steps)
        iL = np.zeros(total_steps)
        vC = np.zeros(total_steps)

        # Condição inicial
        iL[0] = 0 # self.Vo / self.R
        vC[0] = 0 # self.Vo

        # Simulação temporal
        for k in range(total_steps - 1):
            if (time[k] % T_s) < (self.D * T_s):  # Chave fechada
                iL[k + 1] = Ad_00 * iL[k] + Ad_01 * vC[k] + Bd1_0
                vC[k + 1] = Ad_10 * iL[k] + Ad_11 * vC[k] + Bd1_1
            else:  # Chave aberta
                iL[k + 1] = Ad_00 * iL[k] + Ad_01 * vC[k]
                vC[k + 1] = Ad_10 * iL[k] + Ad_11 * vC[k]

        return time, iL, vC