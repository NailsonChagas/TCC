import os
import pty
import time
import math
import fcntl

DAC_MAX_VOLTAGE = 3.3
DAC_BITS = 12
DAC_LEVELS = (1 << DAC_BITS) - 1  # 4095 níveis (2^12 - 1)


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
        self.physical_max_v = 50.0

        # Fator de conversão inicial (3.3 / 50.0)
        self.conversion_factor = self.dac_max_v / self.physical_max_v

        self.sine_freq = 50  # Frequência da senóide gerada [Hz]

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
        print(f" Conversão Ativa: 0 a Vs físico -> 0 a {self.dac_max_v}V no DAC")
        print(f" Resolução do DAC: {DAC_BITS} bits ({self.dac_levels} níveis)")
        print(" Aguardando comandos da GUI do Simulador...")
        print("=" * 60)

    def _send_sine_stream_blocking(self, total_steps: int, fs: float):
        """
        Gera o sinal físico unipolar (0 a Vs), converte para a faixa do DAC (0 a 3.3V)
        e aplica a quantização discreta do DAC.
        """
        print(f"[STREAM] Iniciando envio de {total_steps} pontos (fs = {fs:.2f} Hz)...")
        dt = 1.0 / fs

        for k in range(total_steps):
            elapsed = k * dt

            # 1. Geração do valor físico unipolar na planta (0 a Vs, ex: 0 a 50V)
            normalized_sine = (1.0 + math.sin(2 * math.pi * self.sine_freq * elapsed)) / 2.0
            val_vC_physical = self.physical_max_v * normalized_sine  # Varia de 0 a Vs
            val_iL_physical = (self.physical_max_v / 2.0) * normalized_sine  # Proporcional para corrente

            # 2. Conversão estrita para o domínio do DAC (0 a 3.3V)
            val_vC_dac_ideal = val_vC_physical * self.conversion_factor
            val_iL_dac_ideal = val_iL_physical * self.conversion_factor

            # 3. Quantização dos sinais conforme a resolução em bits do DAC
            val_vC_dac = self.quantize_dac(val_vC_dac_ideal)
            val_iL_dac = self.quantize_dac(val_iL_dac_ideal)

            # Pacote enviado contendo os valores quantizados para o limite do DAC
            telemetry_packet = f"DATA;{k};{elapsed};{val_iL_dac};{val_vC_dac}\n"

            written = False
            while not written:
                try:
                    os.write(self.master_fd, telemetry_packet.encode("utf-8"))
                    written = True
                except (OSError, BlockingIOError):
                    time.sleep(0.002)

            time.sleep(dt)

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

    def _handle_config(self, payload: str):
        parts = payload.split(";")

        if len(parts) == 10:
            _, vs_str, ad00, ad01, bd10, ad10, ad11, bd11, fs_str, steps_str = parts

            try:
                # O Vs recebido da GUI define a tensão física de entrada do Buck (ex: 50V)
                self.physical_max_v = float(vs_str)

                # Recalcula o fator de conversão mantendo o DAC fixo em 3.3V
                self.conversion_factor = self.dac_max_v / self.physical_max_v

                fs = float(fs_str)
                total_steps = int(steps_str)
            except ValueError:
                print("[ERR] Parâmetros numéricos inválidos.")
                return

            print("--- Parâmetros de Discretização Atualizados ---")
            print(f"  Vs Físico (Planta): {self.physical_max_v} V | Teto DAC: {self.dac_max_v} V")
            print(f"  Fator de Conversão: {self.conversion_factor:.6f}")
            print(f"  Ad_00: {ad00} | Ad_01: {ad01} | Bd1_0: {bd10}")
            print(f"  Ad_10: {ad10} | Ad_11: {ad11} | Bd1_1: {bd11}")
            print(f"  fs: {fs:.2f} Hz | Total Steps: {total_steps}")
            print("---------------------------------------------")

            try:
                os.write(self.master_fd, b"OK\n")
                print("[TX] Enviado: OK")
            except Exception:
                pass

            self._send_sine_stream_blocking(total_steps, fs)

        else:
            print(f"[ERR] Pacote incorreto. Esperado 10 campos, recebido {len(parts)}.")

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