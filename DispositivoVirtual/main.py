import os
import pty
import time
import math
import fcntl


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

        # =====================================================================
        # PROTEÇÃO CONTRA TRAVAMENTO DE BUFFER (O_NONBLOCK)
        # Permite que o os.write falhe graciosamente em vez de travar o script
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
        print(" Aguardando comandos da GUI do Simulador...")
        print("=" * 60)

    def _send_sine_stream_blocking(self, total_steps: int, fs: float):
        """
        Envia exatamente N amostras de forma SÍNCRONA.
        Trava o laço principal, mas gerencia inteligentemente o buffer da serial.
        """
        print(f"[STREAM] Iniciando envio de {total_steps} pontos (fs = {fs:.2f} Hz)...")
        dt = 1.0 / fs

        for k in range(total_steps):
            elapsed = k * dt
            val_iL = self.sine_amplitude/2 * math.sin(2 * math.pi * self.sine_freq * elapsed)
            val_vC = self.sine_amplitude * math.sin(2 * math.pi * self.sine_freq * elapsed)

            telemetry_packet = f"DATA;{k};{elapsed};{val_iL};{val_vC}\n"

            # Tenta escrever. Se o buffer do SO estiver cheio, não trava: 
            # apenas aguarda 2ms e tenta novamente.
            written = False
            while not written:
                try:
                    os.write(self.master_fd, telemetry_packet.encode("utf-8"))
                    written = True
                except (OSError, BlockingIOError):
                    time.sleep(0.002)  # Pausa minúscula para a GUI esvaziar o buffer do outro lado

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
        
        if len(parts) == 9:
            _, ad00, ad01, bd10, ad10, ad11, bd11, fs_str, steps_str = parts

            try:
                fs = float(fs_str)
                total_steps = int(steps_str)
            except ValueError:
                print("[ERR] Parâmetros numéricos inválidos.")
                return

            print("--- Parâmetros de Discretização Atualizados ---")
            print(f"  Ad_00: {ad00} | Ad_01: {ad01} | Bd1_0: {bd10}")
            print(f"  Ad_10: {ad10} | Ad_11: {ad11} | Bd1_1: {bd11}")
            print(f"  fs: {fs:.2f} Hz | Total Steps: {total_steps}")
            print("---------------------------------------------")

            try:
                os.write(self.master_fd, b"OK\n")
                print("[TX] Enviado: OK")
            except Exception:
                pass

            # Bloqueia a execução (ignora novos comandos) até concluir o envio
            self._send_sine_stream_blocking(total_steps, fs)

        else:
            print(f"[ERR] Pacote incorreto. Esperado 9 campos, recebido {len(parts)}.")

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
                    # Como o fd é não-bloqueante, os.read levanta erro se não houver dados. Ignoramos.
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