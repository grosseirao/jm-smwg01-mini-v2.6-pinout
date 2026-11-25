"""Grava um .gbl no ZS3L do JM-SMWG01-MINI V2.6 pela rede, sem abrir a placa.

Uso:
    python -I gravar_zs3l.py IP_DO_HUB menu            # só entra no bootloader e volta
    python -I gravar_zs3l.py IP_DO_HUB gravar ARQ.gbl  # grava e inicia o firmware novo

Requisitos no hub (OpenBeken): painel sem login, ponte uarttcp na porta 8888 sem
cliente conectado. Pinos confirmados nesta placa:
    PB4  (índice 36) -> PC01/Bootload do ZS3L: nível BAIXO no reset = bootloader
    PA28 (índice 28) -> RST do ZS3L, ativo em nível baixo

O bootloader (Gecko Bootloader v1.9.2) não usa controle de fluxo: a UART é
reconfigurada com `uartInit 115200`. `stopDriver/startDriver uarttcp` reinicia
o hub pelo watchdog na 1.18.321-mdns6. No fim, o hub é reiniciado para a ponte
voltar com RTS/CTS pelo autoexec.bat.
"""

import socket
import sys
import threading
import time
import urllib.parse
import urllib.request

BOOT_CH = 20
RST_CH = 21
SOH, EOT, ACK, NAK, CAN = 0x01, 0x04, 0x06, 0x15, 0x18


class Hub:
    def __init__(self, host):
        self.host = host

    def cmd(self, c):
        url = f"http://{self.host}/cm?cmnd=" + urllib.parse.quote(c)
        last = None
        for _ in range(8):
            try:
                return urllib.request.urlopen(url, timeout=6).read()
            except Exception as exc:
                last = exc
                time.sleep(0.5)
        raise RuntimeError(f"comando falhou: {c}: {last}")

    def setup_pins(self):
        self.cmd("uartInit 115200")
        time.sleep(1)
        self.cmd(f"backlog setChannel {RST_CH} 1; setPinChannel 28 {RST_CH}; setPinRole 28 Rel; "
                 f"setChannel {BOOT_CH} 1; setPinChannel 36 {BOOT_CH}; setPinRole 36 Rel")
        time.sleep(1)

    def reset(self, boot_low):
        self.cmd(f"setChannel {BOOT_CH} {0 if boot_low else 1}")
        time.sleep(0.2)
        self.cmd(f"setChannel {RST_CH} 0")
        time.sleep(0.5)
        self.cmd(f"setChannel {RST_CH} 1")

    def release_and_restart(self):
        self.cmd(f"setChannel {BOOT_CH} 1")
        time.sleep(0.2)
        self.cmd("backlog setPinRole 36 None; setPinRole 28 None")
        time.sleep(1)
        try:
            self.cmd("restart")
        except RuntimeError:
            pass


class Link:
    """Ponte TCP da porta 8888, lida por uma thread."""

    def __init__(self, host):
        self.sock = socket.create_connection((host, 8888), timeout=5)
        self.sock.settimeout(0.2)
        self.buf = bytearray()
        self.lock = threading.Lock()
        self.alive = True
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while self.alive:
            try:
                d = self.sock.recv(4096)
                if not d:
                    self.alive = False
                    return
                with self.lock:
                    self.buf += d
            except socket.timeout:
                pass
            except OSError:
                self.alive = False
                return

    def send(self, b):
        self.sock.sendall(b)

    def take(self):
        with self.lock:
            b = bytes(self.buf)
            self.buf.clear()
        return b

    def wait_for(self, token, timeout):
        got = b""
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            got += self.take()
            if token in got:
                return got
            time.sleep(0.05)
        return got

    def close(self):
        self.alive = False
        self.sock.close()


def crc16_xmodem(data):
    crc = 0
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return crc


def enter_menu(hub, link):
    hub.reset(boot_low=True)
    for _ in range(6):
        time.sleep(0.8)
        link.send(b"\r\n")
        got = link.wait_for(b"BL >", 1.5)
        if b"BL >" in got:
            print(got.decode(errors="replace").strip().splitlines()[0:5])
            return True
    return False


def xmodem_send(link, data):
    # Espera o 'C' do receptor (modo CRC)
    start = link.wait_for(b"C", 15)
    if b"C" not in start:
        raise RuntimeError(f"bootloader não pediu os dados: {start[-80:]!r}")
    blocks = [data[i:i + 128].ljust(128, b"\xff") for i in range(0, len(data), 128)]
    t0 = time.monotonic()
    for n, block in enumerate(blocks, 1):
        num = n & 0xFF
        crc = crc16_xmodem(block)
        frame = bytes([SOH, num, 0xFF - num]) + block + bytes([crc >> 8, crc & 0xFF])
        for attempt in range(10):
            link.take()
            link.send(frame)
            reply = b""
            end = time.monotonic() + 5
            while time.monotonic() < end and not reply:
                r = link.take()
                reply = bytes(c for c in r if c in (ACK, NAK, CAN))
                if not reply:
                    time.sleep(0.01)
            if reply[:1] == bytes([ACK]):
                break
            if reply[:1] == bytes([CAN]):
                raise RuntimeError(f"bootloader cancelou no bloco {n}")
        else:
            raise RuntimeError(f"bloco {n} sem ACK após 10 tentativas")
        if n % 100 == 0 or n == len(blocks):
            rate = n * 128 / (time.monotonic() - t0)
            print(f"  bloco {n}/{len(blocks)} ({rate / 1024:.1f} kB/s)")
    for _ in range(5):
        link.send(bytes([EOT]))
        r = link.wait_for(bytes([ACK]), 3)
        if bytes([ACK]) in r:
            break
    tail = link.wait_for(b"BL >", 10)
    return tail.decode(errors="replace")


def main():
    host, mode = sys.argv[1], sys.argv[2]
    hub = Hub(host)
    hub.setup_pins()
    link = Link(host)
    try:
        if not enter_menu(hub, link):
            raise RuntimeError("o bootloader não respondeu")
        if mode == "gravar":
            data = open(sys.argv[3], "rb").read()
            print(f"gravando {len(data)} bytes")
            link.take()
            link.send(b"1")
            result = xmodem_send(link, data)
            print("resposta:", result.strip())
            if "complete" not in result.lower():
                raise RuntimeError("o bootloader não confirmou a gravação")
        # Sai do bootloader: '2' (run) e reset com PB4 em nível alto
        link.send(b"2")
        time.sleep(1)
        hub.reset(boot_low=False)
    finally:
        link.close()
        hub.release_and_restart()
    print("pronto: pinos liberados e hub reiniciado")


if __name__ == "__main__":
    main()
