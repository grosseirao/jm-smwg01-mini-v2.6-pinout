"""Testa o proxy serial ESPHome do hub com o mesmo cliente do ZHA.

Uso (com aioesphomeapi, serialx e bellows instalados):
    python -I testar_proxy_serial.py IP_DO_HUB [--so-api]

O servidor ESPHome do hub atende um cliente por vez, e a ponte TCP da porta
8888 impede a assinatura da porta serial enquanto tiver um cliente. Antes do
teste, desative no Home Assistant a entrada ESPHome do hub e a do ZHA.

1. Conecta pela API e mostra a versão da API, as portas seriais no
   DeviceInfo e as capacidades (proxy Bluetooth e portas).
2. Abre a porta "zigbee" pelo bellows em modo PROTOCOL
   (esphome://IP:6053/?port_name=zigbee&mode=protocol), faz o reset do ASH,
   lê a versão do EmberZNet, os parâmetros da rede e o EUI64 e fecha.
"""

import asyncio
import logging
import sys
import time

from aioesphomeapi import APIClient


async def check_api(host: str) -> None:
    client = APIClient(address=host, port=6053, password="", provide_time=False)
    await client.connect(login=True)
    try:
        info = await client.device_info()
        print(f"API {client.api_version}, nome {info.name!r}, versão {info.esphome_version!r}")
        print(f"DeviceInfo.serial_proxies: {info.serial_proxies}")
        caps = await client.device_capabilities_compat(info)
        print(f"Capacidades: bluetooth_proxy={caps.bluetooth_proxy}")
        print(f"Capacidades: serial_proxies={caps.serial_proxies}")
    finally:
        await client.disconnect()


async def check_ezsp(host: str) -> None:
    import zigpy.config as zconf
    from bellows.ezsp import EZSP

    url = f"esphome://{host}:6053/?port_name=zigbee&mode=protocol"
    config = zconf.SCHEMA_DEVICE(
        {
            zconf.CONF_DEVICE_PATH: url,
            zconf.CONF_DEVICE_BAUDRATE: 115200,
            zconf.CONF_DEVICE_FLOW_CONTROL: "hardware",
        }
    )
    ezsp = EZSP(config)
    start = time.monotonic()
    await ezsp.connect(use_thread=False)
    print(f"ASH conectado e resetado em {time.monotonic() - start:.2f} s")
    try:
        brd = await ezsp.get_board_info()
        print(f"Placa: {brd}")
        print(f"Protocolo EZSP: {ezsp.ezsp_version}")
        status, node_type, params = await ezsp.getNetworkParameters()
        print(f"Rede: status={status!r} tipo={node_type!r}")
        print(f"      PAN 0x{params.panId:04x}, canal {params.radioChannel}, EPID {params.extendedPanId}")
        (eui64,) = await ezsp.getEui64()
        print(f"EUI64 do coordenador: {eui64}")
        # Uma rajada de comandos para forçar vários quadros em sequência
        start = time.monotonic()
        for _ in range(50):
            await ezsp.getEui64()
        print(f"50 comandos em {time.monotonic() - start:.2f} s")
    finally:
        await ezsp.disconnect()


async def main() -> None:
    host = sys.argv[1]
    print("== API ESPHome")
    await check_api(host)
    if "--so-api" in sys.argv:
        return
    print("== EZSP pelo proxy serial (modo PROTOCOL)")
    await check_ezsp(host)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO if "-v" not in sys.argv else logging.DEBUG)
    asyncio.run(main())
