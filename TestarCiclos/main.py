import config as cfg
from simulation import simulate_buck_open_loop
from c_generator import generate_c_code
from embedded_tools import compile_for_cortex_m7, analyze_assembly
from visualization import plot_results

if __name__ == "__main__":
    print(f"Iniciando simulação do conversor Buck (n = {cfg.N}, D = {cfg.D})...")
    
    # 1. Simulação
    t_sim, vC, iL, coeffs = simulate_buck_open_loop(cfg.N, cfg.D)
    t_ms = t_sim * 1000

    # 2. Geração e Compilação C
    generate_c_code(coeffs, cfg.N, cfg.D)
    if compile_for_cortex_m7():
        counts, min_cycles, max_cycles = analyze_assembly()
        
        print("\n==========================================")
        print("ANÁLISE DO ASSEMBLY")
        print("==========================================")
        for instruction, count in counts.items():
            print(f"{instruction:10s}: {count:3d}")
        print(f"\nCiclos mínimos: {min_cycles}")
        print(f"Ciclos máximos: {max_cycles}")
        print("==========================================")

    # 3. Gráficos
    plot_results(t_ms, vC, iL, cfg.N, cfg.D)