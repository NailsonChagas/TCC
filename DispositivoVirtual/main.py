import os
import pty
import time
import math


class VirtualUSBDevice:
    def __init__(self, symlink_path: str = "/tmp/ttyVirtual0"):
        self.symlink_path = symlink_path
        self.master_fd = None
        self.slave_fd = None
        self.slave_name = None

        # Parâmetros da Senóide
        self.sine_freq = 50        # Frequência da senóide gerada [Hz]
        self.sine_amplitude = 10.0   # Amplitude da senóide

    def start(self):
        """Cria o par de portas virtuais PTY e gera o link simbólico."""
        self.master_fd, self.slave_fd = pty.openpty()
        self.slave_name = os.ttyname(self.slave_fd)

        if os.path.exists(self.symlink_path):
            os.remove(self.symlink_path)

        os.symlink(self.slave_name, self.symlink_path)

        print("=" * 60)
        print(" Dispositivo Serial Virtual USB ativado!")
        print(f" Portas criadas: {self.slave_name}")
        print(f" Link disponível em: {self.symlink_path}")
        print(" Aguardando comandos da GUI do Simulador...")
        print("=" * 60)

    def _send_sine_stream_blocking(self, total_steps: int, fs: float):
        """
        Envia exatamente N (total_steps) amostras da senóide de forma SÍNCRONA.
        O passo de tempo dt é derivado diretamente de fs.
        """
        print(f"[STREAM] Iniciando envio de {total_steps} pontos (fs = {fs:.2f} Hz)...")
        dt = 1.0 / fs  # Intervalo de tempo real por passo

        for k in range(total_steps):
            elapsed = k * dt
            val = self.sine_amplitude * math.sin(2 * math.pi * self.sine_freq * elapsed)

            # Pacote de dados: DATA;step_index;tempo;valor\n
            telemetry_packet = f"DATA;{k};{elapsed};{val}\n"

            try:
                os.write(self.master_fd, telemetry_packet.encode("utf-8"))
                print(telemetry_packet)
            except OSError:
                print("[STREAM] Erro de escrita. Conexão interrompida.")
                break

            # Pequena pausa proporcional para simular a transmissão do hardware
            time.sleep(dt)

        print(f"[STREAM] Transmissão concluída! ({total_steps} pontos enviados)")

    def process_command(self, raw_line: str):
        """Processa os comandos seriais recebidos e responde sequencialmente."""
        line = raw_line.strip()
        if not line:
            return

        print(f"\n[RX] Recebido: {line}")

        if line.startswith("CONFIG;"):
            self._handle_config(line)
        elif line == "PING":
            os.write(self.master_fd, b"PONG\n")
            print("[TX] Enviado: PONG")
        else:
            print(f"[ERR] Comando não reconhecido: {line}")
            os.write(self.master_fd, b"ERROR: UNKNOWN_CMD\n")

    def _handle_config(self, payload: str):
        """
        Valida o pacote de 9 campos, envia OK\\n e bloqueia a execução
        transmitindo a senóide até concluir total_steps.
        """
        parts = payload.split(";")
        
        # Valida se o payload contém os 9 campos esperados
        # CONFIG ; Ad_00 ; Ad_01 ; Bd1_0 ; Ad_10 ; Ad_11 ; Bd1_1 ; fs ; total_steps
        if len(parts) == 9:
            _, ad00, ad01, bd10, ad10, ad11, bd11, fs_str, steps_str = parts

            try:
                fs = float(fs_str)
                total_steps = int(steps_str)
            except ValueError:
                print("[ERR] Parâmetros numéricos inválidos (fs ou total_steps).")
                os.write(self.master_fd, b"ERROR: INVALID_PARAMETERS\n")
                return

            print("--- Parâmetros de Discretização Atualizados ---")
            print(f"  Ad_00: {ad00} | Ad_01: {ad01} | Bd1_0: {bd10}")
            print(f"  Ad_10: {ad10} | Ad_11: {ad11} | Bd1_1: {bd11}")
            print(f"  fs: {fs:.2f} Hz | Total Steps: {total_steps}")
            print("---------------------------------------------")

            # 1. Envia a resposta de confirmação imediata para destravar a GUI
            os.write(self.master_fd, b"OK\n")
            print("[TX] Enviado: OK")

            # 2. Bloqueia síncronamente enviando as amostras
            self._send_sine_stream_blocking(total_steps, fs)

        else:
            print(f"[ERR] Pacote incorreto. Esperado 9 campos, recebido {len(parts)}.")
            os.write(self.master_fd, b"ERROR: INVALID_PAYLOAD_LENGTH\n")

    def run_forever(self):
        """Loop contínuo de leitura e resposta na porta serial."""
        self.start()
        buffer = ""

        try:
            while True:
                data = os.read(self.master_fd, 1024).decode("utf-8", errors="ignore")
                if not data:
                    continue

                buffer += data

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    self.process_command(line)

        except KeyboardInterrupt:
            print("\nEncerrando dispositivo virtual...")
        finally:
            self.cleanup()

    def cleanup(self):
        """Remove links e fecha os descritores de arquivo."""
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