import numpy as np
from scipy.linalg import expm


FS = 5e3


class CCMError(ValueError):
    """Exceção lançada quando o conversor não opera em CCM."""


class BuckConverterCCM:
    def __init__(
        self,
        Vs: float,
        Vo: float,
        R: float,
        L: float,
        C: float,
        fs: float = FS,
    ) -> None:

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
        cls,
        Vs: float,
        Vo: float,
        Po: float,
        delta_iL: float,
        delta_Vo: float,
        fs: float = FS,
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

    @property
    def D(self) -> float:
        """Razão cíclica nominal."""
        return self.Vo / self.Vs

    @property
    def Lmin(self) -> float:
        """Indutância mínima para operação em CCM."""
        return (1 - self.D) * self.R / (2 * self.fs)

    def simulate(
        self,
        N: int,
        sim_time: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
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

        # ==========================================================
        # Passo de simulação
        # ==========================================================

        T_s = 1.0 / self.fs
        timestep = T_s / N

        total_steps = int(round(sim_time / timestep))

        # ==========================================================
        # Modelo em espaço de estados
        #
        # x = [iL, vC]^T
        #
        # dx/dt = A x + B u
        # ==========================================================

        A = np.array([
            [
                0.0,
                -1.0 / self.L,
            ],
            [
                1.0 / self.C,
                -1.0 / (self.R * self.C),
            ],
        ])

        B_on = np.array([
            [1.0 / self.L],
            [0.0],
        ])

        B_off = np.zeros((2, 1))

        # ==========================================================
        # Discretização exata por ZOH
        # ==========================================================

        Ad = expm(A * timestep)

        A_inv = np.linalg.inv(A)

        Bd_on = (
            A_inv
            @ (Ad - np.eye(2))
            @ B_on
        )

        Bd_off = (
            A_inv
            @ (Ad - np.eye(2))
            @ B_off
        )

        # ==========================================================
        # PWM
        # ==========================================================

        N_on = int(round(self.D * N))

        # ==========================================================
        # Vetores de saída
        # ==========================================================

        time = np.zeros(total_steps)
        iL = np.zeros(total_steps)
        vC = np.zeros(total_steps)

        # ==========================================================
        # Condição inicial
        # ==========================================================

        x = np.array([
            [self.Vo / self.R],
            [self.Vo],
        ])

        # ==========================================================
        # Simulação temporal
        # ==========================================================

        for k in range(total_steps):

            time[k] = k * timestep

            step_in_period = k % N

            pwm = step_in_period < N_on

            if pwm:
                x = Ad @ x + Bd_on * self.Vs
            else:
                x = Ad @ x + Bd_off * self.Vs

            iL[k] = x[0, 0]
            vC[k] = x[1, 0]

        return time, iL, vC