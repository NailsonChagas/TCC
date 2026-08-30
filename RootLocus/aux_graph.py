import control as ct
import matplotlib.pyplot as plt
import numpy as np


# =========================================================
# PLOT CONFIGURATION
# =========================================================
FIG_SIZE = (9, 6)

LINE_WIDTH = 1.2
SPEC_LINE_WIDTH = 1.5

POLE_MARKER_SIZE = 8
POLE_MARKER_WIDTH = 1.5

ZERO_MARKER_SIZE = 8
ZERO_MARKER_WIDTH = 1.5

SPEC_MARKER_SIZE = 100
SPEC_MARKER_WIDTH = 1.5

AXIS_LINE_WIDTH = 1.0

FONT_SIZE = 12
FONT_SIZE_SGRID = 8
TITLE_SIZE = 13

# MATLAB colors
MATLAB_COLORS = [
    '#0072BD',
    '#77AC30',
    '#D95319',
    '#4DBEEE'
]

# Specification region colors
GRID_COLOR = 'gray'
SPEC_COLOR = 'gray'
AXIS_COLOR = 'black'
TEXT_COLOR = '#B0B0B0'


# =========================================================
# FUNCTION: MATLAB-STYLE S-GRID
# =========================================================
def plot_matlab_sgrid(ax, xlim, ylim):

    max_r = np.max(
        np.abs([xlim[0], xlim[1], ylim[0], ylim[1]])
    ) * 1.5

    # Damping ratios
    zetas = [
        0.16, 0.34, 0.5, 0.64,
        0.76, 0.86, 0.94, 0.985
    ]

    # Natural frequencies
    wn_step = 0.5e5
    wns = np.arange(wn_step, max_r, wn_step)

    # =====================================================
    # NATURAL FREQUENCY CIRCLES
    # =====================================================
    theta = np.linspace(np.pi / 2, 3 * np.pi / 2, 200)

    for wn in wns:

        ax.plot(
            wn * np.cos(theta),
            wn * np.sin(theta),
            color=GRID_COLOR,
            linestyle='-',
            linewidth=0.8,
            alpha=0.25,
            zorder=1
        )

        # Frequency labels
        if wn <= 2e5:

            wn_str = f'{wn:.1e}'

            offset_x = -wn
            alignment = 'center'

            if wn == 2e5:
                offset_x = -wn + 5000
                alignment = 'left'

            ax.text(
                offset_x,
                3000,
                wn_str,
                color=TEXT_COLOR,
                fontsize=FONT_SIZE_SGRID,
                ha=alignment,
                va='bottom',
                zorder=1,
                alpha=0.7
            )

    # =====================================================
    # DAMPING RATIO LINES
    # =====================================================
    label_r = 1.45e5

    for zeta in zetas:

        x_end = -max_r * zeta
        y_end = max_r * np.sqrt(1 - zeta**2)

        # Upper line
        ax.plot(
            [0, x_end],
            [0, y_end],
            color=GRID_COLOR,
            linestyle='-',
            linewidth=0.8,
            alpha=0.25,
            zorder=1
        )

        # Lower line
        ax.plot(
            [0, x_end],
            [0, -y_end],
            color=GRID_COLOR,
            linestyle='-',
            linewidth=0.8,
            alpha=0.25,
            zorder=1
        )

        # Upper label
        x_up = -label_r * zeta
        y_up = label_r * np.sqrt(1 - zeta**2)

        ax.text(
            x_up,
            y_up,
            f'{zeta}',
            color=TEXT_COLOR,
            fontsize=FONT_SIZE_SGRID,
            ha='center',
            va='center',
            zorder=1,
            alpha=0.7
        )

        # Lower label
        x_down = -label_r * zeta
        y_down = -label_r * np.sqrt(1 - zeta**2)

        ax.text(
            x_down,
            y_down,
            f'{zeta}',
            color=TEXT_COLOR,
            fontsize=FONT_SIZE_SGRID,
            ha='center',
            va='center',
            zorder=1,
            alpha=0.7
        )


# =========================================================
# FUNCTION: ROOT LOCUS
# =========================================================
def plot_root_locus_matlab(
    sistema,
    titulo="",
    xlabel=r"Eixo Real (rad/s)",
    ylabel=r"Eixo Imaginario (rad/s)"
):

    # =====================================================
    # SYSTEM POLES AND ZEROS
    # =====================================================
    polos = ct.poles(sistema)
    zeros = ct.zeros(sistema)

    print("-" * 50)
    print("POLOS DO SISTEMA (Malha Aberta):")

    if len(polos) > 0:
        for i, p in enumerate(polos):
            print(f"  Polo {i + 1}: {p:.4g}")
    else:
        print("  Nenhum polo.")

    print("\nZEROS DO SISTEMA (Malha Aberta):")

    if len(zeros) > 0:
        for i, z in enumerate(zeros):
            print(f"  Zero {i + 1}: {z:.4g}")
    else:
        print("  Nenhum zero.")

    print("-" * 50)

    # =====================================================
    # FIGURE
    # =====================================================
    fig, ax = plt.subplots(figsize=FIG_SIZE)

    ct.root_locus(
        sistema,
        grid=False,
        xlim=[-2e5, 1e5],
        ylim=[-1.5e5, 1.5e5],
        ax=ax
    )

    # =====================================================
    # ROOT LOCUS BRANCHES AND MARKERS
    # =====================================================
    branch_idx = 0

    for line in ax.lines:

        x_data = line.get_xdata()

        # Root locus branches
        if len(x_data) > 10:

            line.set_color(
                MATLAB_COLORS[
                    branch_idx % len(MATLAB_COLORS)
                ]
            )

            line.set_linewidth(LINE_WIDTH)
            line.set_marker('')
            line.set_zorder(3)

            branch_idx += 1

        # Poles
        elif line.get_marker() in ['x', 'X']:

            line.set_color(MATLAB_COLORS[0])
            line.set_markersize(POLE_MARKER_SIZE)
            line.set_markeredgewidth(POLE_MARKER_WIDTH)
            line.set_zorder(4)

        # Zeros
        elif line.get_marker() == 'o':

            line.set_color(MATLAB_COLORS[0])
            line.set_markerfacecolor('none')
            line.set_markersize(ZERO_MARKER_SIZE)
            line.set_markeredgewidth(ZERO_MARKER_WIDTH)
            line.set_zorder(4)

    # =====================================================
    # S-GRID
    # =====================================================
    plot_matlab_sgrid(
        ax,
        [-2e5, 1e5],
        [-1.5e5, 1.5e5]
    )

    # =====================================================
    # CENTRAL AXES
    # =====================================================
    ax.axhline(
        0,
        color=AXIS_COLOR,
        linestyle=':',
        linewidth=AXIS_LINE_WIDTH,
        alpha=0.6,
        zorder=2
    )

    ax.axvline(
        0,
        color=AXIS_COLOR,
        linestyle=':',
        linewidth=AXIS_LINE_WIDTH,
        alpha=0.6,
        zorder=2
    )

    # =====================================================
    # TITLE AND LABELS
    # =====================================================
    ax.set_title(
        titulo,
        fontsize=TITLE_SIZE,
        fontweight="bold",
        pad=15
    )

    ax.set_xlabel(
        xlabel,
        fontsize=FONT_SIZE
    )

    ax.set_ylabel(
        ylabel,
        fontsize=FONT_SIZE
    )

    # =====================================================
    # AXIS FORMATTING
    # =====================================================
    ax.ticklabel_format(
        style='sci',
        axis='both',
        scilimits=(0, 0),
        useMathText=True
    )

    ax.tick_params(
        axis="both",
        direction="in",
        top=True,
        right=True,
        labelsize=FONT_SIZE,
        width=AXIS_LINE_WIDTH
    )

    for spine in ax.spines.values():
        spine.set_linewidth(AXIS_LINE_WIDTH)
        spine.set_color(AXIS_COLOR)

    ax.set_xlim([-2e5, 1e5])
    ax.set_ylim([-1.5e5, 1.5e5])

    plt.tight_layout()

    return fig, ax


# =========================================================
# FUNCTION: SPECIFICATION REGION
# =========================================================
def plot_specification_region(
    ax,
    zeta_min=0.69,
    sigma_min=7.997e3
):
    """
    Plot the admissible pole region defined by:

        zeta >= zeta_min
        -sigma >= sigma_min

    where:

        zeta     : damping ratio
        sigma    : real part magnitude of the pole
        sigma_min: minimum required decay rate
    """

    # =====================================================
    # AXIS LIMITS
    # =====================================================
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()

    # =====================================================
    # CONSTANTS
    # =====================================================
    radius = np.max(
        np.abs([xlim[0], xlim[1], ylim[0], ylim[1]])
    )

    # =====================================================
    # MINIMUM DECAY RATE
    # =====================================================
    x_sigma = -sigma_min

    ax.axvline(
        x_sigma,
        color=SPEC_COLOR,
        linestyle='--',
        linewidth=SPEC_LINE_WIDTH,
        alpha=0.8,
        zorder=2
    )

    # =====================================================
    # MINIMUM DAMPING RATIO
    # =====================================================
    theta = np.arccos(zeta_min)

    x_end = -radius * zeta_min
    y_end = radius * np.sin(theta)

    # Upper boundary
    ax.plot(
        [0, x_end],
        [0, y_end],
        color=SPEC_COLOR,
        linestyle='--',
        linewidth=SPEC_LINE_WIDTH,
        alpha=0.8,
        zorder=2
    )

    # Lower boundary
    ax.plot(
        [0, x_end],
        [0, -y_end],
        color=SPEC_COLOR,
        linestyle='--',
        linewidth=SPEC_LINE_WIDTH,
        alpha=0.8,
        zorder=2
    )

    # =====================================================
    # ADMISSIBLE REGION
    # =====================================================
    x = np.linspace(
        xlim[0],
        x_sigma,
        500
    )

    y_limit = (
        (-x)
        * np.sqrt(1 - zeta_min**2)
        / zeta_min
    )

    ax.fill_between(
        x,
        -y_limit,
        y_limit,
        color=SPEC_COLOR,
        alpha=0.08,
        zorder=0
    )

    # =====================================================
    # DESIRED DOMINANT POLES
    # =====================================================
    omega_n_min = sigma_min / zeta_min

    omega_d = (
        omega_n_min
        * np.sqrt(1 - zeta_min**2)
    )

    ax.scatter(
        [-sigma_min, -sigma_min],
        [omega_d, -omega_d],
        marker='x',
        s=POLE_MARKER_SIZE**2,
        color=SPEC_COLOR,
        linewidths=SPEC_MARKER_WIDTH,
        zorder=5
    )

    return ax