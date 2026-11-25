# OpenRTL8720D com mDNS

A partir da `1.18.321-mdns5`, esta versão parte do commit `323814d` do
OpenBeken, de 24/11/2026, posterior à tag `1.18.321`, e do SDK
OpenRTL8720D `ad3d02c`. Até a `mdns4`, a base era a tag `1.18.321`
(`168cba5`). O commit `2efff41b` do OpenBeken, incluído nessa base, muda
o proxy BLE no código compartilhado com o RTL8720D. A varredura só
começa quando a pilha Bluetooth está pronta e é reiniciada após 60 s
sem anúncios. Só a thread do servidor da API ESPHome envia pelo socket,
e as outras threads enfileiram os quadros. As conexões GATT ativas do
mesmo commit ficam desligadas no RTL8720D, porque o
`ENABLE_BT_PROXY_GATT` só é definido na variante `btproxy` do
RTL87X0C.

O driver usa o serviço mDNS do SDK Realtek.
Inicia quando a interface Wi-Fi já tem um IP e anuncia
`gateway-zigbee-ble-<sufixo>.local`. O sufixo contém os últimos três
bytes do MAC do Wi-Fi, escritos como seis dígitos hexadecimais em
minúsculas. O driver atualiza o anúncio quando o IP muda.

O painel web é anunciado como `_http._tcp.local.`. Com a ponte
`uarttcp` ativa, o firmware anuncia também
`_zigbee-coordinator._tcp.local.` na porta 8888, com
`radio_type=ezsp` e `serial_number` derivado do MAC completo do Wi-Fi.
O ZHA pode usar o IP e a porta do anúncio se o Zeroconf estiver ativo
e receber o multicast da LAN.

A partir da `1.18.321-mdns4`, com o driver `ESPHomeAPI` ativo, o
firmware anuncia também `_esphomelib._tcp.local.` na porta 6053. É o
tipo de serviço que a integração ESPHome do Home Assistant procura, e o
proxy BLE do OpenBeken fala o protocolo da API nativa do ESPHome. O TXT
leva `mac` (MAC do Wi-Fi em hexadecimal minúsculo, sem separadores),
`network=wifi`, `platform=RTL8720D` e `friendly_name` (o nome do
dispositivo configurado no OpenBeken).

Na mesma versão, a API ESPHome passou a informar como nome do nó, no
`HelloResponse` e no `DeviceInfoResponse`, o mesmo rótulo do mDNS
(`gateway-zigbee-ble-<sufixo>`). O Home Assistant guarda o nome
descoberto e recusa a conexão quando o `HelloResponse` traz outro nome.
O `friendly_name` continua sendo o nome configurado no OpenBeken. Sem
o responder mDNS ativo, a API volta a usar o nome do OpenBeken.

## Proxy serial do ESPHome (mdns6)

A `1.18.321-mdns6` acrescenta o driver `ESPHomeSerial`
(`drv_esphome_serial_proxy.c`). Ele expõe a UART0 do ZS3L como a porta
`zigbee` do proxy serial da API nativa do ESPHome, que o ZHA usa pelo
endereço `esphome-hass://`. O bellows abre essa porta em modo PROTOCOL e
deixa de enviar os ACKs do ASH. O hub passa a confirmar os quadros DATA
do rádio localmente, então o tempo limite de ACK do rádio não depende do
Wi-Fi. O RTS/CTS fica sempre ligado, porque os fios existem na placa.

Para isso a API anuncia a versão 1.17, responde ao
`DeviceCapabilitiesRequest` (proxy Bluetooth e porta serial) e declara
a porta também no `DeviceInfoResponse`. A ponte `uarttcp` e o proxy
serial se excluem: com um cliente na porta 8888, a assinatura da porta
serial recebe `PORT_IN_USE`, e vice-versa. O comando `ESPHomeSerialStatus`
escreve no log o estado e os contadores de bytes e de ACKs.

A lógica do ACK foi comparada com o bellows 1.2.1 em 11 casos, num
programa de teste no PC. No hub, o
[testar_proxy_serial.py](testar_proxy_serial.py) abriu a porta em modo
PROTOCOL, leu o EmberZNet 6.5.5 e completou 50 comandos com 57 ACKs do
hub e nenhum byte perdido. Depois, o ZHA usou a porta com o EmberZNet
7.4.3, sem perdas.

Problema conhecido: `stopDriver uarttcp` seguido de `startDriver
uarttcp` reinicia o hub pelo watchdog de hardware. Use `uartInit` para
trocar a configuração da UART sem reiniciar a ponte.

## Imagem OTA

A imagem compilada fica em
[outputs/OpenBeken-mdns](../../outputs/OpenBeken-mdns/). Para atualizar
o WBRG1, use o arquivo `OpenRTL8720D_1.18.321-mdns6_ota.img` no painel
OTA do OpenBeken. A imagem atualiza o WBRG1. O firmware do rádio ZS3L
fica na flash do próprio rádio.

Com o MAC `00:33:7A:DA:B1:13`, o endereço é
`gateway-zigbee-ble-dab113.local`. Para configuração manual, o ZHA
aceita o endereço TCP `socket://192.168.3.143:8888` com o tipo
`ezsp`. O uso do hostname nesse endereço depende do resolvedor do
host do Home Assistant.

## Recompilar

Use Linux ou WSL com GNU Arm Embedded Toolchain `10.3-2021.10` no
`PATH`. Em um checkout separado do código:

```bash
git clone https://github.com/openshwprojects/OpenBK7231T_App.git
cd OpenBK7231T_App
git checkout 323814d3448070c03993272827fbd8eac3e3d5aa
git submodule update --init sdk/OpenRTL8720D
patch_dir=/caminho/absoluto/para/src/openbeken-mdns
git apply "$patch_dir/openbeken.patch"
git -C sdk/OpenRTL8720D apply "$patch_dir/realtek-sdk.patch"
make -j4 APP_VERSION=1.18.321-mdns6 APP_NAME=OpenRTL8720D VARIANT=default OpenRTL8720D
```

O arquivo OTA sai em `output/1.18.321-mdns6/`. O patch da `mdns4` só
se aplica à tag `1.18.321` e está no histórico do repositório.

## Verificação

A imagem foi compilada e verificada pelo cabeçalho OTA1 e pelo checksum
do pacote. O teste simulado conferiu os registros do painel e do
coordenador, a inicialização e parada da ponte, a troca de IP e a
suspensão dos anúncios no modo hotspot.

A instalação OTA foi verificada na placa física. Depois do reinício, o
hub reportou `1.18.321-mdns3` e retornou os registros PTR, SRV, TXT e
A do coordenador em consulta multicast na LAN. No Home Assistant Core
2026.10.2, após habilitar `zeroconf:`, o navegador Zeroconf listou o
coordenador e o serviço foi resolvido pelo host. O cartão de configuração
automática do ZHA ainda não apareceu no painel de integrações.

A `1.18.321-mdns4` foi compilada sem avisos nos arquivos alterados e
instalada por OTA no hub. O script
[verificar_servicos.py](verificar_servicos.py), sem dependências,
confirmou na LAN:

- `gateway-zigbee-ble-dab113._esphomelib._tcp.local` com SRV na porta
  6053 e TXT `mac=00337adab113`, `network=wifi`, `platform=RTL8720D` e
  `friendly_name=OpenRTL8720D_7ADAB113`;
- o anúncio `_zigbee-coordinator._tcp` na porta 8888, sem mudança;
- a API ESPHome na porta 6053 informando o nome
  `gateway-zigbee-ble-dab113` no `HelloResponse` e no
  `DeviceInfoResponse`, com a versão `1.18.321-mdns4` e
  `bluetooth_proxy_feature_flags=96` (anúncios brutos e estado/modo).

Na mdns3, a API informava o nome `OpenRTL8720D_7ADAB113`.

Uso: `python -I verificar_servicos.py IP_DO_HUB`. Com adaptadores
virtuais no Windows, o script envia a consulta pela interface da rota
até o hub.

No Home Assistant 2026.10.2, o cartão de descoberta da integração
ESPHome apareceu. A entrada foi adicionada sem pedir senha nem chave,
com o título `gateway-zigbee-ble-dab113` e o dispositivo
`OpenRTL8720D_7ADAB113`, os dois com o MAC `00:33:7A:DA:B1:13`. Falta
confirmar no monitor de anúncios da integração Bluetooth que os
anúncios BLE chegam tendo o hub como origem.

O cartão `hci0` que aparece descoberto na integração Bluetooth é outro
adaptador. Ele pertence ao host do Home Assistant, com endereço
`02:FF:87:02:49:B4`, lido no `debugfs` do host.

A `1.18.321-mdns5` foi compilada sem avisos nos arquivos alterados e
instalada por OTA no hub. Os registros mDNS dos dois serviços ficaram
iguais aos da `mdns4`. O servidor da API ESPHome dessa base atende um
cliente por vez, e cada conexão nova substitui a anterior. Com o Home
Assistant conectado, ele reconecta em seguida e derruba a conexão do
`verificar_servicos.py`. Por isso a versão e o nome informados pela API
não foram lidos pelo script nessa versão. Falta conferir no Home
Assistant a versão do dispositivo ESPHome e a ponte Zigbee.

### Endereço Bluetooth do hub

A API informa `bluetooth_mac_address` igual ao MAC do Wi-Fi. O driver
do OpenBeken lê a efuse lógica `0x190` (`bt_get_mac_address`) e, se ela
estiver vazia, usa o MAC do Wi-Fi no lugar. Com a efuse vazia, o
controlador usaria o endereço padrão do SDK, `89:51:12:36:28:11`. A
linha `BT ADDRESS` que o SDK imprime na UART de log durante o `BTInit`
resolve qual é o caso. Ela ainda não foi capturada.
