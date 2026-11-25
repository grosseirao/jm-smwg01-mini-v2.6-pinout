"""Troca os pinos de UART do ncp-uart-zs3l-hw-115200-7.4.3-12.5.gbl para a JM-SMWG01-MINI V2.6.

O firmware original usa os pinos padrão do ZS3L:
    TX PA06, RX PA05, CTS PB01, RTS PB00
Esta placa liga o rádio pelos pinos do modo gateway (medidos por continuidade):
    TX PD00, RX PD01, CTS PA03, RTS PA04

A estrutura de inicialização do UARTDRV é montada na pilha (função em 0x4be4)
com dois literais (0x4c58 e 0x4c5c). Layout lido por UARTDRV_InitUart (0x7cf4):
    +5 txPort, +6 txPin, +7 rxPort, +8 rxPin, +9 ctsPort, +10 ctsPin,
    +11 rtsPort, +12 rtsPin (vem de um registrador zerado), +14 uartNum.
O rtsPin é trocado nas três instruções que o leem (ldrb rX,[r4,#12] -> movs rX,#4).

A aplicação não tem assinatura nem CRC próprio (signatureType 0); só o CRC32 do
GBL, na tag END, é recalculado.

Uso: python -I corrigir_pinos_743.py ENTRADA.gbl SAIDA.gbl
"""

import struct
import sys
import zlib

PROG_TAG = 0xFD0303FD
END_TAG = 0xFC0404FC
BASE = 0x4000

# (endereço, bytes originais, bytes novos)
PATCHES = [
    (0x4C58, bytes.fromhex("21000600"), bytes.fromhex("21030003")),  # b4, TX=PD00, rxPort=D
    (0x4C5C, bytes.fromhex("05010101"), bytes.fromhex("01000300")),  # RX pino 1, CTS=PA03, rtsPort=A
    (0x7D56, bytes.fromhex("237b"), bytes.fromhex("0423")),  # ldrb r3,[r4,#12] -> movs r3,#4
    (0x7DC6, bytes.fromhex("217b"), bytes.fromhex("0421")),  # ldrb r1,[r4,#12] -> movs r1,#4
    (0x7DE2, bytes.fromhex("217b"), bytes.fromhex("0421")),  # ldrb r1,[r4,#12] -> movs r1,#4
]


def main():
    src, dst = sys.argv[1], sys.argv[2]
    d = bytearray(open(src, "rb").read())

    i = 0
    prog_data = end_off = None
    while i + 8 <= len(d):
        tag, ln = struct.unpack_from("<II", d, i)
        if tag == PROG_TAG:
            addr = struct.unpack_from("<I", d, i + 8)[0]
            assert addr == BASE, hex(addr)
            prog_data = i + 12
        if tag == END_TAG:
            end_off = i
            break
        i += 8 + ln
    assert prog_data is not None and end_off is not None

    stored = struct.unpack_from("<I", d, end_off + 8)[0]
    assert zlib.crc32(bytes(d[:end_off + 8])) == stored, "CRC do GBL original não confere"

    for addr, old, new in PATCHES:
        o = prog_data + (addr - BASE)
        if bytes(d[o:o + len(old)]) != old:
            raise SystemExit(f"0x{addr:x}: esperado {old.hex()}, encontrado {bytes(d[o:o + len(old)]).hex()}")
        d[o:o + len(new)] = new
        print(f"0x{addr:x}: {old.hex()} -> {new.hex()}")

    struct.pack_into("<I", d, end_off + 8, zlib.crc32(bytes(d[:end_off + 8])))
    open(dst, "wb").write(d)
    print(f"gravado {dst} ({len(d)} bytes)")


if __name__ == "__main__":
    main()
