import matplotlib.pyplot as plt
import config as cfg

def plot_results(t_ms, vC, iL, n, d):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

    ax1.plot(t_ms, vC, color='tab:blue', lw=1.5)
    ax1.set_ylabel(r'$v_C$ (V)', fontsize=cfg.FONT_LABEL)
    ax1.tick_params(axis='both', labelsize=cfg.FONT_TICKS)
    ax1.grid(True, linestyle='--', alpha=0.6)

    ax2.plot(t_ms, iL, color='tab:red', lw=1.5)
    ax2.set_xlabel('Tempo (ms)', fontsize=cfg.FONT_LABEL)
    ax2.set_ylabel(r'$i_L$ (A)', fontsize=cfg.FONT_LABEL)
    ax2.tick_params(axis='both', labelsize=cfg.FONT_TICKS)
    ax2.grid(True, linestyle='--', alpha=0.6)

    plt.tight_layout()
    output_filename = f"buck_aberto_n{n}_D{str(d).replace('.', '_')}.png"
    plt.savefig(output_filename, dpi=cfg.DPI, bbox_inches='tight')
    plt.show()
    
    print(f"[Visualização] Gráfico salvo como '{output_filename}'.")