"""Verifica os anuncios mDNS e a API ESPHome do hub, sem dependencias.

Uso:
    python verificar_servicos.py [IP_DO_HUB]

1. Pergunta por multicast quem anuncia _esphomelib._tcp e
   _zigbee-coordinator._tcp e imprime os registros PTR, SRV, TXT e A.
2. Se um IP for dado, conecta na porta 6053 em texto puro e imprime o
   nome do HelloResponse e os campos do DeviceInfoResponse, incluindo as
   flags de proxy Bluetooth.
"""

import socket
import struct
import sys
import time

MDNS_GROUP = "224.0.0.251"
MDNS_PORT = 5353
SERVICES = ["_esphomelib._tcp.local", "_zigbee-coordinator._tcp.local"]
TYPES = {1: "A", 12: "PTR", 16: "TXT", 33: "SRV"}


def encode_name(name):
    out = b""
    for label in name.strip(".").split("."):
        out += bytes([len(label)]) + label.encode()
    return out + b"\x00"


def build_query(names):
    header = struct.pack(">HHHHHH", 0, 0, len(names), 0, 0, 0)
    body = b"".join(encode_name(n) + struct.pack(">HH", 12, 1) for n in names)
    return header + body


def read_name(data, offset):
    labels = []
    jumped = False
    end = offset
    for _ in range(64):
        length = data[offset]
        if length & 0xC0 == 0xC0:
            pointer = ((length & 0x3F) << 8) | data[offset + 1]
            if not jumped:
                end = offset + 2
            jumped = True
            offset = pointer
            continue
        if length == 0:
            if not jumped:
                end = offset + 1
            break
        labels.append(data[offset + 1:offset + 1 + length].decode(errors="replace"))
        offset += 1 + length
    return ".".join(labels), end


def parse_records(data):
    _, flags, qd, an, ns, ar = struct.unpack(">HHHHHH", data[:12])
    if not flags & 0x8000:
        return []
    offset = 12
    for _ in range(qd):
        _, offset = read_name(data, offset)
        offset += 4
    records = []
    for _ in range(an + ns + ar):
        name, offset = read_name(data, offset)
        rtype, _, ttl, rdlen = struct.unpack(">HHIH", data[offset:offset + 10])
        offset += 10
        rdata = data[offset:offset + rdlen]
        if rtype == 12:
            value, _ = read_name(data, offset)
        elif rtype == 33:
            _, _, port = struct.unpack(">HHH", rdata[:6])
            target, _ = read_name(data, offset + 6)
            value = f"{target}:{port}"
        elif rtype == 16:
            items, i = [], 0
            while i < len(rdata):
                n = rdata[i]
                items.append(rdata[i + 1:i + 1 + n].decode(errors="replace"))
                i += 1 + n
            value = items
        elif rtype == 1:
            value = socket.inet_ntoa(rdata)
        else:
            value = None
        offset += rdlen
        if rtype in TYPES:
            records.append((TYPES[rtype], name, ttl, value))
    return records


def local_address_towards(host):
    # Com adaptadores virtuais (WSL, VirtualBox), o multicast pode sair pela
    # interface errada. Usa o endereco local da rota ate o hub.
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect((host, 9))
        return probe.getsockname()[0]
    finally:
        probe.close()


def query_mdns(interface="0.0.0.0", timeout=4.0):
    sockets = []
    # Respostas multicast chegam na 5353; respostas "legacy unicast" voltam
    # para a porta de origem da pergunta.
    listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        listener.bind(("", MDNS_PORT))
        mreq = struct.pack("4s4s", socket.inet_aton(MDNS_GROUP), socket.inet_aton(interface))
        listener.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        sockets.append(listener)
    except OSError as exc:
        print(f"(sem escuta na 5353: {exc})")
        listener.close()
    asker = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    asker.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
    asker.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(interface))
    asker.bind((interface, 0))
    sockets.append(asker)

    query = build_query(SERVICES)
    seen = set()
    deadline = time.time() + timeout
    next_send = 0.0
    while time.time() < deadline:
        if time.time() >= next_send:
            asker.sendto(query, (MDNS_GROUP, MDNS_PORT))
            next_send = time.time() + 1.0
        for s in sockets:
            s.settimeout(0.1)
            try:
                data, source = s.recvfrom(9000)
            except (socket.timeout, OSError):
                continue
            try:
                records = parse_records(data)
            except Exception:
                continue
            for record in records:
                key = (record[0], record[1], str(record[3]))
                if key not in seen and (
                    "_esphomelib" in record[1] or "_zigbee-coordinator" in record[1]
                    or "gateway-zigbee-ble" in record[1]
                ):
                    seen.add(key)
                    print(f"  {record[0]:4} {record[1]} ttl={record[2]} -> {record[3]}  (de {source[0]})")
    for s in sockets:
        s.close()
    return seen


def varint(value):
    out = b""
    while value >= 0x80:
        out += bytes([(value & 0x7F) | 0x80])
        value >>= 7
    return out + bytes([value])


def read_varint(buf, i):
    result = shift = 0
    while True:
        b = buf[i]
        i += 1
        result |= (b & 0x7F) << shift
        if not b & 0x80:
            return result, i
        shift += 7


def pb_string(field, text):
    data = text.encode()
    return varint((field << 3) | 2) + varint(len(data)) + data


def pb_varint(field, value):
    return varint(field << 3) + varint(value)


def pb_decode(payload):
    fields, i = {}, 0
    while i < len(payload):
        key, i = read_varint(payload, i)
        field, wire = key >> 3, key & 7
        if wire == 0:
            value, i = read_varint(payload, i)
        elif wire == 2:
            n, i = read_varint(payload, i)
            value = payload[i:i + n].decode(errors="replace")
            i += n
        else:
            break
        fields[field] = value
    return fields


def frame(msg_type, payload=b""):
    return b"\x00" + varint(len(payload)) + varint(msg_type) + payload


class FrameReader:
    def __init__(self, sock):
        self.sock = sock
        self.buf = b""

    def read(self):
        while True:
            if self.buf and self.buf[0] != 0:
                raise RuntimeError("quadro nao e texto puro (API com criptografia?)")
            try:
                size, i = read_varint(self.buf, 1)
                msg_type, i = read_varint(self.buf, i)
                if len(self.buf) >= i + size:
                    payload = self.buf[i:i + size]
                    self.buf = self.buf[i + size:]
                    return msg_type, payload
            except IndexError:
                pass
            chunk = self.sock.recv(1024)
            if not chunk:
                raise RuntimeError("conexao fechada pelo hub")
            self.buf += chunk


def query_api(host):
    with socket.create_connection((host, 6053), timeout=5) as sock:
        reader = FrameReader(sock)
        sock.sendall(frame(1, pb_string(1, "verificar_servicos") + pb_varint(2, 1) + pb_varint(3, 10)))
        msg_type, payload = reader.read()
        hello = pb_decode(payload)
        print(f"  HelloResponse (tipo {msg_type}): api {hello.get(1)}.{hello.get(2)}, "
              f"servidor={hello.get(3)!r}, nome={hello.get(4)!r}")
        sock.sendall(frame(3) + frame(9))
        info = None
        for _ in range(4):
            msg_type, payload = reader.read()
            if msg_type == 10:
                info = pb_decode(payload)
                break
        if info is None:
            print("  DeviceInfoResponse nao recebido")
            return hello, None
        labels = {2: "nome", 3: "mac", 4: "versao", 6: "modelo", 12: "fabricante",
                  13: "friendly_name", 15: "bluetooth_proxy_feature_flags", 18: "bluetooth_mac"}
        for field, label in labels.items():
            if field in info:
                print(f"  {label}: {info[field]!r}")
        flags = info.get(15, 0)
        names = {1: "passive_scan", 2: "active_connections", 4: "remote_caching",
                 8: "pairing", 16: "cache_clearing", 32: "raw_advertisements", 64: "state_and_mode"}
        print("  flags BLE:", ", ".join(n for bit, n in names.items() if flags & bit) or "nenhuma")
        sock.sendall(frame(5))  # DisconnectRequest
        return hello, info


def main():
    interface = local_address_towards(sys.argv[1]) if len(sys.argv) > 1 else "0.0.0.0"
    print(f"Consulta mDNS pela interface {interface}:")
    if not query_mdns(interface):
        print("  nenhuma resposta dos servicos procurados")
    if len(sys.argv) > 1:
        print(f"API ESPHome em {sys.argv[1]}:6053:")
        try:
            query_api(sys.argv[1])
        except (RuntimeError, OSError) as exc:
            # Desde o OpenBeken 323814d o servidor atende um cliente por vez e
            # cada conexao nova substitui a anterior. Com o Home Assistant
            # conectado, ele derruba este teste ao reconectar.
            print(f"  falhou: {exc}")
            print("  Se o Home Assistant estiver conectado ao hub, ele retoma a conexao "
                  "e derruba este teste. Confira a versao pela pagina do dispositivo no HA.")


if __name__ == "__main__":
    main()
