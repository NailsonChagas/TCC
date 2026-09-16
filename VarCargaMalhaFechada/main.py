import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import control as ct
import time
import os

s = ct.TransferFunction.s

V_S = 50

P_percentage = np.linspace(10, 100, 1001)

R_base = 41.7
L = 1.5e-3
C = 0.18e-6

C_s = (0.001033*s + 67.15) / s

H_s = 9.87e8 / (
    s**2
    + 5.441e4 * s
    + 9.87e8
)


# ============================================================
# CONFIGURAÇÃO E CHECKPOINT
# ============================================================

CHECKPOINT_FILE = "checkpoint_variacao_R.npz"
SAVE_EVERY = 500

n_total = len(P_percentage)

t = np.linspace(
    0,
    6e-3,
    7000
)

respostas = np.full(
    (n_total, len(t)),
    np.nan
)

polos_re = []
polos_im = []

zeros_re = []
zeros_im = []

ultima_iteracao = -1


# ============================================================
# CARREGAMENTO DO CHECKPOINT
# ============================================================

if os.path.exists(CHECKPOINT_FILE):

    print("\nCheckpoint encontrado. Carregando dados...")

    checkpoint = np.load(
        CHECKPOINT_FILE,
        allow_pickle=True
    )

    respostas_checkpoint = checkpoint["respostas"]

    # Verifica se o checkpoint possui a mesma quantidade
    # de condições de potência do estudo atual
    if respostas_checkpoint.shape == respostas.shape:

        ultima_iteracao = int(
            checkpoint["ultima_iteracao"]
        )

        respostas = respostas_checkpoint

        polos_re = list(
            checkpoint["polos_re"]
        )

        polos_im = list(
            checkpoint["polos_im"]
        )

        zeros_re = list(
            checkpoint["zeros_re"]
        )

        zeros_im = list(
            checkpoint["zeros_im"]
        )

        print(
            f"Continuando a partir da iteração "
            f"{ultima_iteracao + 1}/{n_total}"
        )

    else:

        print(
            "\nO checkpoint existente possui "
            "dimensões incompatíveis com o estudo atual."
        )

        print(
            "O cálculo será reiniciado do início.\n"
        )

else:

    print(
        "\nNenhum checkpoint encontrado. "
        "Começando do início.\n"
    )


# ============================================================
# LOOP DE CÁLCULO
# ============================================================

inicio_total = time.perf_counter()

for i in range(
    ultima_iteracao + 1,
    n_total
):

    p = P_percentage[i]

    inicio = time.perf_counter()

    # --------------------------------------------------------
    # Resistência de carga
    # --------------------------------------------------------

    R = R_base / (p / 100)

    # --------------------------------------------------------
    # Função de transferência da planta
    # --------------------------------------------------------

    if p==0:
        G_s = (V_S/(L*C)) / (s**2) + (1/(L*C))
    else:
        G_s = (
                V_S * R
            ) / (
                (s**2) * R * L * C
                + s * L
                + R
            )

    # --------------------------------------------------------
    # Função de transferência em malha fechada
    # --------------------------------------------------------

    T_s = ct.feedback(
        C_s * G_s,
        H_s
    )

    T_s = ct.minreal(
        T_s,
        verbose=False
    )

    # --------------------------------------------------------
    # Resposta ao degrau
    # --------------------------------------------------------

    _, y = ct.step_response(
        T_s,
        T=t
    )

    respostas[i, :] = y

    # --------------------------------------------------------
    # Polos
    # --------------------------------------------------------

    poles = ct.poles(T_s)

    polos_re.append(
        np.real(poles)
    )

    polos_im.append(
        np.imag(poles)
    )

    # --------------------------------------------------------
    # Zeros
    # --------------------------------------------------------

    zeros = ct.zeros(T_s)

    zeros_re.append(
        np.real(zeros)
    )

    zeros_im.append(
        np.imag(zeros)
    )

    # --------------------------------------------------------
    # Tempo da iteração
    # --------------------------------------------------------

    fim = time.perf_counter()

    print(
        f"[{i+1}/{n_total}] "
        f"P = {p:.2f}% | "
        f"R = {R:.4f} ohm | "
        f"Tempo: {fim - inicio:.6f} s"
    )

    # --------------------------------------------------------
    # Salvar checkpoint
    # --------------------------------------------------------

    if (
        (i + 1) % SAVE_EVERY == 0
        or i == n_total - 1
    ):

        np.savez_compressed(
            CHECKPOINT_FILE,

            ultima_iteracao=i,

            respostas=respostas,

            polos_re=np.array(
                polos_re,
                dtype=object
            ),

            polos_im=np.array(
                polos_im,
                dtype=object
            ),

            zeros_re=np.array(
                zeros_re,
                dtype=object
            ),

            zeros_im=np.array(
                zeros_im,
                dtype=object
            )
        )

        print(
            f"\n>>> CHECKPOINT SALVO "
            f"em {i+1}/{n_total}\n"
        )


fim_total = time.perf_counter()

print(
    f"\nTempo total de cálculo: "
    f"{fim_total - inicio_total:.2f} s"
)

# ============================================================
# MAPAS DE CORES
# ============================================================

FATOR_ESCURO = 0.91


def escurecer_cmap(
    cmap_original,
    fator,
    n=256
):

    cores = cmap_original(
        np.linspace(0, 1, n)
    )

    cores[:, :3] = np.clip(
        cores[:, :3] * fator,
        0,
        1
    )

    return mcolors.LinearSegmentedColormap.from_list(
        f"{cmap_original.name}_dark_{fator}",
        cores
    )


norm = mcolors.Normalize(
    vmin=min(P_percentage),
    vmax=max(P_percentage)
)


# ------------------------------------------------------------
# Colormap da resposta ao degrau
# ------------------------------------------------------------

cmap_step = escurecer_cmap(
    plt.cm.jet_r,
    FATOR_ESCURO
)


# ------------------------------------------------------------
# Colormap dos polos
# ------------------------------------------------------------

# cmap_poles = escurecer_cmap(
#     plt.cm.YlOrRd_r,
#     FATOR_ESCURO
# )

cmap_poles = escurecer_cmap(
    plt.cm.YlOrBr,
    1
)


# ------------------------------------------------------------
# Colormap dos zeros
# ------------------------------------------------------------

cmap_zeros = escurecer_cmap(
    plt.cm.inferno_r,
    1
)


# ------------------------------------------------------------
# ScalarMappable
# ------------------------------------------------------------

sm_step = cm.ScalarMappable(
    cmap=cmap_step,
    norm=norm
)

sm_poles = cm.ScalarMappable(
    cmap=cmap_poles,
    norm=norm
)

sm_zeros = cm.ScalarMappable(
    cmap=cmap_zeros,
    norm=norm
)


for sm in [
    sm_step,
    sm_poles,
    sm_zeros
]:

    sm.set_array([])


# ============================================================
# CRIAÇÃO DAS FIGURAS
# ============================================================

# Figura 1:
# Resposta ao degrau

fig1, ax1 = plt.subplots(
    figsize=(6, 5)
)


# Figura 2:
# Polos e zeros

fig4, ax4 = plt.subplots(
    figsize=(8, 5)
)

# ============================================================
# PLOTAGEM DAS RESPOSTAS, POLOS E ZEROS
# ============================================================

print("\nGerando gráficos...")


for i, p in enumerate(P_percentage):

    # --------------------------------------------------------
    # Associação de cores
    # --------------------------------------------------------

    c_step = cmap_step(
        norm(p)
    )

    c_pole = cmap_poles(
        norm(p)
    )

    c_zero = cmap_zeros(
        norm(p)
    )

    # --------------------------------------------------------
    # Resposta ao degrau
    # --------------------------------------------------------

    ax1.plot(
        t * 1e3,
        respostas[i],
        color=c_step,
        alpha=0.6
    )

    # --------------------------------------------------------
    # Polos
    # --------------------------------------------------------

    ax4.scatter(
        polos_re[i],
        polos_im[i],
        marker='x',
        s=45,
        color=c_pole,
        alpha=0.7
    )

    # --------------------------------------------------------
    # Zeros
    # --------------------------------------------------------

    if len(zeros_re[i]) > 0:

        ax4.scatter(
            zeros_re[i],
            zeros_im[i],
            marker='o',
            facecolors='none',
            edgecolors=c_zero,
            linewidths=1.8,
            s=65,
            alpha=0.85
        )


# ============================================================
# FIGURA 1 — RESPOSTA AO DEGRAU
# ============================================================

ax1.axvline(
    1,
    color='purple',
    linestyle='-.',
    label='Limite de Tempo (1 ms)'
)

ax1.set_xlabel(
    "Tempo [ms]"
)

ax1.set_ylabel(
    "Amplitude"
)

ax1.grid(
    True
)

ax1.legend(
    loc="lower right"
)


cbar1 = fig1.colorbar(
    sm_step,
    ax=ax1
)

cbar1.set_label(
    'Variação da Potência Nominal (%)'
)


# ============================================================
# FIGURA 2 — POLOS E ZEROS
# ============================================================

ax4.axhline(
    0,
    color='black',
    linewidth=0.8
)

ax4.axvline(
    0,
    color='black',
    linewidth=0.8
)

ax4.set_xlabel(
    "Parte Real [rad/s]"
)

ax4.set_ylabel(
    "Parte Imaginária [rad/s]"
)

ax4.grid(
    True
)


# ------------------------------------------------------------
# Colorbar dos polos
# ------------------------------------------------------------

cbar4_p = fig4.colorbar(
    sm_poles,
    ax=ax4,
    pad=0.02
)

cbar4_p.set_label(
    'Escala da Potência Nominal (%) - Polos [x]'
)


# ------------------------------------------------------------
# Colorbar dos zeros
# ------------------------------------------------------------

cbar4_z = fig4.colorbar(
    sm_zeros,
    ax=ax4,
    pad=0.09
)

cbar4_z.set_label(
    'Escala da Potência Nominal (%) - Zeros [o]'
)


# ============================================================
# AJUSTE E SALVAMENTO
# ============================================================

fig1.tight_layout()

fig4.tight_layout()


# ------------------------------------------------------------
# Resposta ao degrau
# ------------------------------------------------------------

fig1.savefig(
    "resposta_degrau_variacao_R.png",
    dpi=500,
    bbox_inches="tight"
)


# ------------------------------------------------------------
# Polos e zeros
# ------------------------------------------------------------

fig4.savefig(
    "polos_e_zeros_variacao_R.png",
    dpi=500,
    bbox_inches="tight"
)


# ============================================================
# EXIBIÇÃO
# ============================================================

plt.show()