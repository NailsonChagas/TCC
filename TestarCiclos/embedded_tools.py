import subprocess
from pathlib import Path

def compile_for_cortex_m7(filename="buck_model.c"):
    source = Path(filename)
    object_file = source.with_suffix(".o")
    assembly_file = source.with_suffix(".s")
    compiler = "arm-none-eabi-gcc"

    try:
        subprocess.run([compiler, "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print("\n[Erro] arm-none-eabi-gcc não encontrado. Instale com: sudo apt install gcc-arm-none-eabi\n")
        return False

    flags = ["-O3", "-mcpu=cortex-m7", "-mthumb", "-mfpu=fpv5-sp-d16", "-mfloat-abi=hard"]
    
    # Compila Objeto
    subprocess.run([compiler, *flags, "-c", str(source), "-o", str(object_file)], check=True)
    # Compila Assembly
    subprocess.run([compiler, *flags, "-S", str(source), "-o", str(assembly_file)], check=True)
    
    print("[Embedded Tools] Compilação Cortex-M7 concluída com sucesso.")
    return True

def analyze_assembly(filename="buck_model.s"):
    # https://community.arm.com/forums/f/architectures-and-processors-forum/9930/cortex-m7-vfma-usage/32157
    instruction_cycles = {
    # Operações de ponto flutuante:
        # 1 ciclo por instrução, conforme medições experimentais
        # realizadas em Cortex-M7.
        "vmul.f32": (1, 1),
        "vfma.f32": (1, 1),
        "vadd.f32": (1, 1),

        # Acesso à memória:
        # VLDR medido em DTCM com possibilidade de uso do dado
        # no ciclo seguinte. VSTR não foi medido diretamente;
        # adotado valor conservador de 2 ciclos.
        "vldr": (1, 1),
        "vstr": (2, 2),

        # Controle de fluxo:
        # valores conservadores adotados devido à dependência
        # do pipeline e do comportamento de desvios.
        "cbz": (2, 2),
        "b":   (2, 2),
        "bx":  (2, 2),
    }
    
    instruction_count = {}
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip().lower()
        if not line or line.startswith("@"):
            continue
        
        instruction = line.split()[0]
        if instruction in ("vldr.32", "vldr"): instruction = "vldr"
        if instruction in ("vstr.32", "vstr"): instruction = "vstr"

        if instruction in instruction_cycles:
            instruction_count[instruction] = instruction_count.get(instruction, 0) + 1

    min_cycles = sum(count * instruction_cycles[instr][0] for instr, count in instruction_count.items())
    max_cycles = sum(count * instruction_cycles[instr][1] for instr, count in instruction_count.items())

    return instruction_count, min_cycles, max_cycles