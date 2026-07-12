from utils.constants import FS

class CCMError(ValueError):
    """Exceção lançada quando o conversor não opera em CCM."""

class BuckConverterCCM:
    """
    Representação de um conversor Buck operando em Modo de Condução Contínua (CCM).

    As equações de projeto e análise implementadas nesta classe são baseadas em:
    Hart, D. W. (2010). Power Electronics. McGraw-Hill Professional.
    """
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
        """
        Cria um conversor Buck em CCM a partir dos parâmetros de projeto.

        A resistência da carga, a indutância e a capacitância são calculadas
        utilizando as equações de projeto para conversores Buck operando em
        modo de condução contínua (CCM).

        As equações implementadas são baseadas em:
        Hart, D. W. (2010). Power Electronics. McGraw-Hill Professional.

        Args:
            Vs: Tensão de entrada (V).
            Vo: Tensão de saída (V).
            Po: Potência de saída (W).
            delta_iL: Ripple de corrente do indutor (A).
            delta_Vo: Ripple de tensão da saída (V).
            fs: Frequência de chaveamento (Hz).

        Returns:
            Uma instância de ``BuckConverterCCM`` com os componentes calculados.

        Raises:
            CCMError: Se a indutância calculada não satisfizer a condição de
                operação em modo de condução contínua (CCM).
        """
        R = Vo**2 / Po
        D = Vo / Vs

        L = Vo * (1 - D) / (delta_iL * fs)
        C = Vo * (1 - D) / (8 * L * delta_Vo * fs**2)

        return cls(Vs, Vo, R, L, C, fs)

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
        """Razão cíclica."""
        return self.Vo / self.Vs

    @property
    def Po(self) -> float:
        """Potência de saída."""
        return self.Vo**2 / self.R

    @property
    def iL(self) -> float:
        """Corrente média no indutor."""
        return self.Vo / self.R

    @property
    def Lmin(self) -> float:
        """Indutância mínima para operação em CCM."""
        return (1 - self.D) * self.R / (2 * self.fs)

    @property
    def delta_iL(self) -> float:
        """Ripple de corrente no indutor."""
        return self.Vo * (1 - self.D) / (self.L * self.fs)

    @property
    def delta_Vo(self) -> float:
        """Ripple de tensão na saída."""
        return (
            self.Vo
            * (1 - self.D)
            / (8 * self.L * self.C * self.fs**2)
        )

    def __repr__(self) -> str:
        return (
            "BuckConverterCCM("
            f"Vs={self.Vs}, "
            f"Vo={self.Vo}, "
            f"R={self.R}, "
            f"L={self.L}, "
            f"C={self.C}, "
            f"fs={self.fs}"
            ")"
        )