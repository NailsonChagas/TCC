import os
import pty
import time
import math
import fcntl

DAC_MAX_VOLTAGE = 3.3
DAC_BITS = 12
DAC_LEVELS = (1 << DAC_BITS) - 1  # 4095 níveis (2^12 - 1)

DUTY_CYCLE = 0.5
N = 100  # Frequência de chaveamento real do conversor físico (5 kHz)

class VirtualUSBDevice:
    def __init__(self, symlink_path: str = "/tmp/ttyVirtual0"):
        self.symlink_path = symlink_path
        self.master_fd = None
        self.slave_fd = None
        self.slave_name = None

        # O DAC do microcontrolador sempre tem teto fixo em 3.3V
        self.dac_max_v = DAC_MAX_VOLTAGE
        self.dac_levels = DAC_LEVELS

        # O Vs que vem do payload será o teto físico do sistema (ex: 50.0V)
        self.vC_max = 0.0
        self.iL_max = 0.0

        # Fator de conversão inicial (3.3 / 50.0)
        self.conversion_factor_vC = 0.0
        self.conversion_factor_iL = 0.0

        # Inicialização dos coeficientes do espaço de estados
        self.ad00 = 0.0
        self.ad01 = 0.0
        self.bd10 = 0.0
        self.ad10 = 0.0
        self.ad11 = 0.0
        self.bd11 = 0.0

    def quantize_dac(self, voltage: float) -> float:
        """
        Quantiza um valor de tensão imitando a resolução discreta do DAC em hardware.
        """
        # Saturação na faixa do DAC (0V a 3.3V)
        if voltage < 0.0: voltage = 0.0
        elif voltage > self.dac_max_v: voltage = self.dac_max_v

        code = voltage * float(self.dac_levels) / self.dac_max_v
        code_quantized = int(code + 0.5)
        return (float(code_quantized) * self.dac_max_v) / float(self.dac_levels)

    def start(self):
        """Cria o par de portas virtuais PTY e gera o link simbólico."""
        self.master_fd, self.slave_fd = pty.openpty()
        self.slave_name = os.ttyname(self.slave_fd)

        # =====================================================================
        # PROTEÇÃO CONTRA TRAVAMENTO DE BUFFER (O_NONBLOCK)
        # =====================================================================
        flags = fcntl.fcntl(self.master_fd, fcntl.F_GETFL)
        fcntl.fcntl(self.master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        if os.path.exists(self.symlink_path):
            os.remove(self.symlink_path)

        os.symlink(self.slave_name, self.symlink_path)

        print("=" * 60)
        print(" Dispositivo Serial Virtual USB ativado!")
        print(f" Portas criadas: {self.slave_name}")
        print(f" Link disponível em: {self.symlink_path}")
        print(f" Conversão Ativa: 0 a {self.dac_max_v}V no DAC")
        print(f" Resolução do DAC: {DAC_BITS} bits ({self.dac_levels} níveis)")
        print(" Aguardando comandos da GUI do Simulador...")
        print("=" * 60)

    def _handle_config(self, payload: str):
        parts = payload.split(";")

        if len(parts) == 11:
            _, vc_str, il_str, ad00, ad01, bd10, ad10, ad11, bd11, fs_str, steps_str = parts

            try:
                # O Vs recebido da GUI define a tensão física de entrada do Buck (ex: 50V)
                self.vC_max = float(vc_str)
                self.iL_max = float(il_str)

                # Salva os coeficientes do espaço de estados
                self.ad00 = float(ad00)
                self.ad01 = float(ad01)
                self.bd10 = float(bd10)
                self.ad10 = float(ad10)
                self.ad11 = float(ad11)
                self.bd11 = float(bd11)
                
                # Recalcula o fator de conversão mantendo o DAC fixo em 3.3V
                self.conversion_factor_vC = self.dac_max_v / self.vC_max
                self.conversion_factor_iL = self.dac_max_v / self.iL_max

                # fs_str recebe fs_sim (Frequência sobreamostrada da simulação)
                fs_sim = float(fs_str)
                total_steps = int(steps_str)
            except ValueError:
                print("[ERR] Parâmetros numéricos inválidos.")
                return

            print("--- Parâmetros de Discretização Atualizados ---")
            print(f"  Vc Max (Planta): {self.vC_max} V |  iL Max (Planta): {self.iL_max} V | Teto DAC: {self.dac_max_v} V")
            print(f"  Fator de Conversão vC: {self.conversion_factor_vC:.6f}")
            print(f"  Fator de Conversão iL: {self.conversion_factor_iL:.6f}")
            print(f"  Ad_00: {self.ad00} | Ad_01: {self.ad01} | Bd1_0: {self.bd10}")
            print(f"  Ad_10: {self.ad10} | Ad_11: {self.ad11} | Bd1_1: {self.bd11}")
            print(f"  fs_sim: {fs_sim:.2f} Hz | Total Steps: {total_steps}")
            print("---------------------------------------------")

            try:
                os.write(self.master_fd, b"OK\n")
                print("[TX] Enviado: OK")
            except Exception:
                pass

            # Inicia a simulação com as matrizes configuradas
            self._run_buck_simulation(total_steps, fs_sim)

        else:
            print(f"[ERR] Pacote incorreto. Esperado 10 campos, recebido {len(parts)}.")

    def _run_buck_simulation(self, total_steps: int, fs_sim: float):
        """
        Gera o sinal simulando a planta do Buck com os coeficientes de espaço de estados,
        converte para a faixa do DAC (0 a 3.3V) e aplica a quantização discreta do DAC.
        """
        print(f"[STREAM] Iniciando simulação do Buck ({total_steps} pontos, fs_sim = {fs_sim:.2f} Hz)...")
        
        # O período de chaveamento fixo da planta física (5 kHz)
        T_s = 1.0 / (fs_sim/N)
        
        # O passo de tempo da simulação de alta resolução (dt) baseado na sobreamostragem
        dt = 1.0 / fs_sim 

        # Condições iniciais
        iL_val = 0.0
        vC_val = 0.0

        for k in range(total_steps):
            elapsed = k * dt

            # 1. Conversão para o domínio do DAC (0 a 3.3V) e Quantização dos sinais conforme a resolução do DAC
            # seria a saida do dac mas estou só avaliando a telemetria
            val_vC_dac = self.quantize_dac(vC_val * self.conversion_factor_vC)
            val_iL_dac = self.quantize_dac(iL_val * self.conversion_factor_iL)

            # 2. Empacotamento e transmissão
            telemetry_packet = f"DATA;{k};{elapsed:.6e};{iL_val};{vC_val}\n"

            written = False
            while not written:
                try:
                    os.write(self.master_fd, telemetry_packet.encode("utf-8"))
                    written = True
                except (OSError, BlockingIOError):
                    time.sleep(0.002)

            # 4. Atualização dos estados para k+1 (Simulação temporal)
            # O resto da divisão funciona perfeitamente agora, pois dt é muito menor que T_s
            if (elapsed % T_s) < (DUTY_CYCLE * T_s):  
                # Chave Fechada
                next_iL = self.ad00 * iL_val + self.ad01 * vC_val + self.bd10
                next_vC = self.ad10 * iL_val + self.ad11 * vC_val + self.bd11
            else:  
                # Chave Aberta
                next_iL = self.ad00 * iL_val + self.ad01 * vC_val
                next_vC = self.ad10 * iL_val + self.ad11 * vC_val

            iL_val = next_iL
            vC_val = next_vC

            # Atraso real para não travar a GUI (ajustar conforme necessidade)
            time.sleep(dt) # time.sleep(0.001) -> colocar 0.001 se travar, por enquanto funcionou ok

        print(f"[STREAM] Transmissão concluída! ({total_steps} pontos enviados)")

    def process_command(self, raw_line: str):
        line = raw_line.strip()
        if not line:
            return

        print(f"\n[RX] Recebido: {line}")

        if line.startswith("CONFIG;"):
            self._handle_config(line)
        elif line == "PING":
            try:
                os.write(self.master_fd, b"PONG\n")
            except Exception:
                pass
            print("[TX] Enviado: PONG")
        else:
            print(f"[ERR] Comando não reconhecido: {line}")
            try:
                os.write(self.master_fd, b"ERROR: UNKNOWN_CMD\n")
            except Exception:
                pass

    def run_forever(self):
        self.start()
        buffer = ""

        try:
            while True:
                try:
                    data = os.read(self.master_fd, 1024).decode("utf-8", errors="ignore")
                    if data:
                        buffer += data
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            self.process_command(line)
                except (OSError, BlockingIOError):
                    pass

                time.sleep(0.01)

        except KeyboardInterrupt:
            print("\nEncerrando dispositivo virtual...")
        finally:
            self.cleanup()

    def cleanup(self):
        if os.path.exists(self.symlink_path):
            os.remove(self.symlink_path)
        if self.master_fd:
            os.close(self.master_fd)
        if self.slave_fd:
            os.close(self.slave_fd)
        print("Dispositivo encerrado limpo.")


if __name__ == "__main__":
    device = VirtualUSBDevice(symlink_path="/tmp/ttyVirtual0")
    device.run_forever()