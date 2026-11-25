# Pinagem da JM-SMWG01-MINI V2.6

Placa identificada pela inscrição `JM-SMWG01-MINI`, revisão `V2.6`, data `2024/06/25`. O módulo branco **ZS3L (EFR32MG21)** é o rádio Zigbee. O módulo azul **WBRG1 (RTL8721CSM)** é o módulo Wi‑Fi/Bluetooth.

## Configuração do OpenBeken

O WBRG1 roda o **OpenBeken 1.18.321**, na variante OpenRTL8720D. O ZS3L conserva o firmware **EmberZNet 6.5.5.0 build 432**, com protocolo EZSP 7. Os [scripts do OpenBeken](src/openbeken-config/) ficam em `src`. O [registro dos testes](outputs/OpenBeken-configuracao-validada/LEIA-ME.txt) fica em `outputs`.

### LEDs e botão

| Componente | GPIO | Configuração | Comportamento |
|---|---|---|---|
| LED vermelho | PA25 (25) | `WifiLED`, canal 1 | Aceso fixo com o Wi-Fi conectado. Pisca durante a conexão. |
| LED azul | PB22 (54) | `LED`, canal 2 | Aceso enquanto um controlador está conectado à ponte Zigbee por TCP. |
| Botão | PB23 (55) | `Btn`, canal 3 | O clique curto alterna o canal 3. Vincular esse evento à janela de pareamento ainda depende do controlador Zigbee. |

Segurar o botão por **5 segundos** está configurado para chamar o hotspot nativo do OpenBeken. O painel fica em `http://192.168.4.1` e exige o login de administração. Em **Config → WiFi & Web**, é possível configurar a nova rede. O script programa um reinício após **5 minutos** para tentar a rede salva caso a configuração não seja concluída. A regra foi gravada no hub e a abertura do hotspot pelo botão físico ainda precisa ser testada. O gesto de reset de fábrica está desativado.

### Imagem com a configuração embutida

Os scripts podem ir para a placa junto com o firmware, já dentro do LittleFS do OpenBeken. Assim não é preciso enviá-los pela interface web.

1. Gere a imagem do LittleFS. Ela leva o `autoexec.bat` e o `wifi-recovery.bat` desta pasta:
   ```powershell
   python -m pip install "littlefs-python==0.12.0"
   python src\openbeken-config\build_lfs_image.py --output-dir outputs
   ```
   O resultado é `outputs\OpenRTL8720D-lfs-8MB-at-0x3C6000.bin`.
2. Grave no WBRG1, na mesma sessão do gravador:

   | Arquivo | Endereço |
   |---|---|
   | `OpenRTL8720D_1.18.321.bin` | `0x000000` |
   | `OpenRTL8720D-lfs-8MB-at-0x3C6000.bin` | `0x3C6000` |

   O gravador usado foi o `RTLNFlasher` do BK7231GUIFlashTool. Ele grava em endereço escolhido. Os links do código de terceiros estão em [src/TERCEIROS.md](src/TERCEIROS.md).

   Não junte os dois num arquivo único de 8 MiB. Entre 0x116000 e 0x3C6000 ficam a configuração do OpenBeken (Wi-Fi e login) e dados do sistema.
3. No primeiro boot, o `autoexec.bat` já configura os LEDs e o botão e inicia a ponte Zigbee e o proxy BLE. Só falta configurar o Wi-Fi da unidade pelo hotspot.

Como o gerador replica o OpenBeken 1.18.321 (`src/littlefs/our_lfs.c`):
- No RTL8720D com flash acima de 2 MiB, o LittleFS vai de 0x3C6000 até o fim da flash. Em 8 MiB são 0x43A000 bytes, ou 1082 blocos de 4 KiB.
- Parâmetros: `read/prog_size` 1, `cache` 16, `lookahead` 16 e `block_cycles` 500.
- O OpenBeken usa o littlefs 2.4, que só lê o **formato de disco 2.0**. O gerador fixa essa versão, porque a biblioteca do Python gravaria a 2.1 por padrão.
- O `lfs_mount` confere o número de blocos no superbloco. Com outro tamanho, o OpenBeken reformata a área e os scripts somem. Para outra capacidade de flash, use `--flash-mb`.
- O arquivo vai só até o último bloco usado pelo littlefs. O resto da área pode continuar com dados antigos, porque o littlefs só lê os blocos que estão na árvore dele.

O gerador remove o BOM e troca CRLF por LF. Ele recusa scripts que não sejam ASCII.

Estado: a imagem foi montada de novo com os mesmos parâmetros e os dois arquivos conferiram. A gravação nesse endereço e o boot com ela **ainda não foram testados no hub**.

### Como aplicar em outra placa V2.6 pela interface web

1. Instale o **OpenRTL8720D 1.18.321** no WBRG1. Acesse o painel do OpenBeken e configure o Wi-Fi da nova unidade.
2. Copie [autoexec.bat](src/openbeken-config/autoexec.bat) e [wifi-recovery.bat](src/openbeken-config/wifi-recovery.bat) para a raiz do LittleFS pela interface web.
3. Reinicie o hub. O `autoexec.bat` configura os dois LEDs e o botão, inicia a ponte Zigbee na porta **8888** com RTS/CTS e inicia o proxy BLE na porta **6053**. O `wifi-recovery.bat` roda quando o botão chama o hotspot.

Se estiver atualizando uma unidade configurada pelo procedimento anterior, remova a linha `startDriver uarttcp 115200 512 2 1` de **Startup Command** para a ponte ser iniciada uma só vez pelo novo `autoexec.bat`.

A imagem padrão do OpenBeken e os scripts são instalados em etapas separadas. As credenciais e os dispositivos pareados pertencem a cada unidade.

### Validação e integração

Uma tomada Zigbee pareou pelo controlador local Bellows/zigpy e respondeu à leitura de estado, inclusive depois de reconectar o controlador. Um cliente de teste também recebeu anúncios BLE pela API ESPHome enquanto a ponte Zigbee estava em uso.

A integração na instância final do Home Assistant ainda precisa ser testada. Para o ZHA, o endereço da ponte é `socket://IP_DO_HUB:8888` com rádio **Silicon Labs EZSP**. Para o proxy BLE, a integração é **ESPHome**, em `IP_DO_HUB:6053`.

### Nome na rede local

A [versão OTA com mDNS](src/openbeken-mdns/README.md) anuncia `gateway-zigbee-ble-<sufixo>.local` após conectar ao Wi-Fi. Cada unidade usa os últimos três bytes do próprio MAC do Wi-Fi. No hub com MAC `00:33:7A:DA:B1:13`, o nome `gateway-zigbee-ble-dab113.local` foi verificado na rede local após a atualização OTA.

A versão `1.18.321-mdns3` também anuncia `_zigbee-coordinator._tcp.local.` na porta `8888` enquanto a ponte Zigbee estiver ativa. A publicação dos registros do coordenador foi confirmada por multicast na LAN. A descoberta no painel do Home Assistant depende do Zeroconf da instância.

A versão `1.18.321-mdns4` acrescenta `_esphomelib._tcp.local.` na porta `6053` enquanto o proxy BLE (`ESPHomeAPI`) estiver ativo. É por esse tipo de serviço que a integração ESPHome do Home Assistant encontra o proxy Bluetooth. A API passa a informar o mesmo nome do mDNS. A versão foi instalada por OTA e os registros do novo serviço e o nome da API foram confirmados na LAN. No Home Assistant 2026.10.2, o hub apareceu como descoberto na integração ESPHome e foi adicionado como `gateway-zigbee-ble-dab113`, com o MAC `00:33:7A:DA:B1:13`. A chegada de anúncios BLE com o hub como origem ainda não foi conferida no monitor de anúncios.

A versão `1.18.321-mdns5` leva o mesmo patch para o commit `323814d` do OpenBeken, que traz as correções do proxy BLE de 24/11/2026. Ela foi instalada por OTA e os anúncios mDNS foram confirmados na LAN. A versão informada ao Home Assistant e a ponte Zigbee nessa versão ainda precisam ser conferidas.

## P1 na placa fotografada

Olhe a **face dos componentes**, com o **USB-C para cima**, o ZS3L à esquerda e o WBRG1 à direita. P1 é a fileira de quatro furos logo abaixo do WBRG1, acima de P2, junto à inscrição **烧录** (gravação). Conte da esquerda para a direita.

```text
                USB-C ↑
       ZS3L branco     WBRG1 azul
                       ●  ●  ●  ●    P1
                       1  2  3  4
                       ●  ●  ●  ●    P2
```

| P1 | Sinal do WBRG1 | Continuidade medida | Ligação ao FT232RL |
|---|---|---|---|
| 1 | GND | W1 e carcaça metálica do USB-C, 0,2 Ω | GND |
| 2 | LogTX / PA7, saída do módulo | W23, 0,2 Ω | RXD |
| 3 | LogRX / PA8, entrada do módulo | W24, 0,2 Ω | TXD para comunicação bidirecional. Livre na captura de logs |
| 4 | EN, habilitação | W2, 0,2 Ω | Livre no uso normal |

Os 0,2 Ω medidos coincidiram com a resistência das pontas juntas. GND e LogTX funcionaram na captura de logs. A ligação de LogRX também foi usada no backup e na gravação verificada do WBRG1.

Use **USB–TTL com lógica de 3,3 V**. Alimente a placa pelo próprio USB-C e deixe o VCC do adaptador livre. Na entrada em modo de programação que funcionou nesta unidade, o resistor de **1 kΩ** ficou entre **P1-1 e P1-2** durante a ligação do USB-C e foi removido cerca de um segundo depois. Os logs e a leitura verificada usaram **115200 baud, 8N1** na COM12 deste computador.

## Como localizar os terminais dos módulos

As referências W e Z foram atribuídas durante as medições. Use a mesma orientação da foto para localizá-las. Os números W e Z não devem ser tratados como a numeração oficial dos datasheets.

| Módulo | Borda | Referências |
|---|---|---|
| WBRG1 azul, antena à direita | Superior | W1 a W9, da esquerda para a direita |
| WBRG1 azul | Esquerda | W10 a W16, de cima para baixo |
| WBRG1 azul | Inferior | W17 a W25, da esquerda para a direita |
| ZS3L branco, antena à esquerda | Superior | Z1 a Z8, da esquerda para a direita |
| ZS3L branco | Inferior | Z9 a Z16, da esquerda para a direita |
| ZS3L branco | Direita | Z17 a Z22, de cima para baixo |

## Comunicação entre o Wi‑Fi e o Zigbee

Esta é a UART interna usada pela ponte do OpenBeken. A consulta local ao ZS3L funcionou a **115200 baud com RTS/CTS** e identificou **EmberZNet 6.5.5.0, build 432**, em modo coordenador. Os dois fios de dados foram confirmados por continuidade em 25/11/2026: **Z6 (PD00) ↔ W8 (PA19, RX0)** e **Z7 (PD01) ↔ W13 (PA18, TX0)**, sem ligação entre W8 e W13. A placa usa os pinos do modo gateway do datasheet, e não o PA05/PA06 padrão do módulo. O RTS/CTS segue o datasheet e não foi medido.

| WBRG1 | ZS3L no modo gateway | Função |
|---|---|---|
| PA18 / TX0 | PD01 / UART_RX | Dados do WBRG1 para o rádio |
| PA19 / RX0 | PD00 / UART_TX | Dados do rádio para o WBRG1 |
| PA16 / RTS0 | PA03 / UART_CTS | Controle de fluxo |
| PA17 / CTS0 | PA04 / UART_RTS | Controle de fluxo |

Os logs do firmware original identificam **PB4** como controle de boot do Zigbee, e a análise do código indicava **PA28** como reset do ZS3L. As duas ligações foram confirmadas por continuidade, com a placa desligada:

| WBRG1 | Ref. | ZS3L | Ref. | Função no ZS3L |
|---|---|---|---|---|
| PA28 (pino 3) | W7 | RST (pino 1) | Z9 | Reset, ativo em nível baixo |
| PB4 (pino 7) | W3 | PC01 / Bootload (pino 2) | Z10 | Entra no bootloader se estiver em nível baixo quando o reset é solto |

Desenhos das duas pinagens na orientação da placa, com o que foi medido: [WBRG1](docs/pinagem-wbrg1.svg) e [ZS3L](docs/pinagem-zs3l.svg).

### Pinos do ZS3L nas referências Z

A numeração oficial vem do datasheet da Tuya. A posição na placa foi confirmada pelos GND (Z8, Z17 e Z19) e pelo 3V3 (Z16 ligado a Z22).

| Ref. | Pino | Função | Ref. | Pino | Função |
|---|---|---|---|---|---|
| Z9 | 1 | RST | Z1 | 16 | TXD (PA05) |
| Z10 | 2 | PC01 / Bootload | Z2 | 15 | RXD (PA06) |
| Z11 | 3 | RST1, desconectado | Z3 | 14 | PB01 |
| Z12 | 4 | PC00 | Z4 | 13 | PB00 |
| Z13 | 5 | PA00 | Z5 | 12 | PC02 |
| Z14 | 6 | PA03, CTS no modo gateway | Z6 | 11 | PD00, TX no modo gateway |
| Z15 | 7 | PA04, RTS no modo gateway | Z7 | 10 | PD01, RX no modo gateway |
| Z16 | 8 | 3V3 | Z8 | 9 | GND |

### Entrada no bootloader do ZS3L pela rede

Testado no hub em 25/11/2026, sem gravar nada no rádio. Com o **PB4 em nível baixo** e um pulso de **0,5 s** em nível baixo no PA28, o ZS3L respondeu pela ponte da porta 8888 com o menu `Gecko Bootloader v1.9.2` (`1. upload gbl`, `2. run`, `3. ebl info`). Com o PB4 em nível alto, o mesmo pulso reinicia o firmware normal. Isso segue o datasheet. Na placa irmã do projeto `zs3l-ncp-flash-over-network`, o nível era o contrário.

Comandos do OpenBeken usados (índice do PB4 = 36, do PA28 = 28):

1. `uartInit 115200`: a UART sem controle de fluxo, que o bootloader não usa.
2. `backlog setChannel 21 1; setPinChannel 28 21; setPinRole 28 Rel; setChannel 20 1; setPinChannel 36 20; setPinRole 36 Rel`
3. `setChannel 20 0`, depois `setChannel 21 0`, meio segundo de espera, e `setChannel 21 1`. Dois `setChannel` seguidos num mesmo `backlog` geram um pulso curto demais.
4. Para sair: `setChannel 20 1` e o mesmo pulso de reset. Depois `setPinRole 36 None`, `setPinRole 28 None` e `restart`, para a ponte voltar com RTS/CTS pelo `autoexec.bat`.

O [gravar_zs3l.py](src/zs3l-project/gravar_zs3l.py) faz esse procedimento e envia o `.gbl` por XMODEM‑CRC pela ponte.

### Coordenador do Zigbee2MQTT da casa

Desde 25/11/2026, o hub é o coordenador da rede Zigbee da casa. A rede é a do Zigbee2MQTT 2.14.2 (canal 15, PAN `0xDA05`, 9 dispositivos Tuya), que antes usava um ESP32‑C6 com o adaptador `zboss`. O Zigbee2MQTT roda em Docker (`zigbee2mqtt-coex`) no host do Home Assistant. A configuração passou a ser:

```yaml
serial:
  port: tcp://192.168.3.143:8888
  adapter: ember
```

O adaptador `ember` do zigbee-herdsman 11.0.0 recusa backups de outra pilha (`[BACKUP] Current backup file is not for EmberZNet stack`). O `coordinator_backup.json` do ZBOSS foi adaptado com três mudanças:

- `metadata.internal.ezspVersion = 13`;
- `stack_specific.ezsp.hashed_tclk` aleatório, porque os dispositivos do backup não têm chave de link própria;
- contador de quadros da chave de rede +100.000, porque o backup era de 1,5 h antes da troca e o `formNetwork` usa o valor sem margem.

Com isso, o herdsman montou a rede a partir do backup (`FORM_BACKUP`), com o IEEE do próprio hub (`0x6ce4a4fffeaf615c`), sem gravação permanente. Os 9 dispositivos voltaram em alguns minutos. O LQI subiu de no máximo ~70 com o C6 para 120 a 196. O original ficou como `coordinator_backup.zboss-original.json` na pasta de dados do Zigbee2MQTT.

Para voltar ao C6: religar o C6, restaurar o `coordinator_backup.zboss-original.json` e repor `adapter: zboss` com `port: tcp://127.0.0.1:6638`.

O pedido `zigbee2mqtt/bridge/request/restart` deixou o Zigbee2MQTT parado com o ZBOSS: ele não reconectou ao C6 sem reset do rádio. Evite reinícios pelo MQTT nessa combinação.

### Firmware do ZS3L: EmberZNet 7.4.3 com os pinos desta placa

O ZS3L roda o **EmberZNet 7.4.3 (EZSP 13)** desde 25/11/2026. O bellows conversa com ele pela ponte da porta 8888, a 115200 com RTS/CTS, e lê o mesmo EUI64 (`6c:e4:a4:ff:fe:af:61:5c`). A rede gravada no 6.5.5 não foi preservada.

Os firmwares prontos para o ZS3L usam os pinos padrão do módulo. Esta placa usa os do modo gateway:

| Sinal do rádio | Firmwares prontos | Esta placa |
|---|---|---|
| TX | PA06 | PD00 |
| RX | PA05 | PD01 |
| CTS | PB01 | PA03 |
| RTS | PB00 | PA04 |

O [corrigir_pinos_743.py](src/zs3l-project/corrigir_pinos_743.py) parte do `ncp-uart-zs3l-hw-115200-7.4.3-12.5.gbl` e troca 7 bytes da estrutura de inicialização do UARTDRV, mais as três instruções que leem o pino do RTS. Ele confere os bytes originais e recalcula o CRC do GBL. A aplicação não tem assinatura nem CRC próprio. O arquivo gerado, `ncp-uart-zs3l-jm-smwg01-pd00-pd01-hw-115200-7.4.3.gbl`, tem SHA‑256 `c9d97a3ce9581a09818ecb2b8c43b9631eb97eec06a34941c794c2a3f1d39d00`.

Nesse firmware, o bellows informa que o IEEE só pode ser gravado de forma permanente (`can_burn_userdata_custom_eui64`), e não regravado.

Antes dele, o `zs3l_zigbee_ncp_8.2.2.0_115200.gbl` do projeto `dzerik/zs3l-ncp-flash-over-network` foi gravado e não respondeu em nenhuma velocidade: ele usa os pinos padrão. Esse teste sobrescreveu o EmberZNet 6.5.5 original, do qual não havia cópia.

Na `1.18.321-mdns6`, `stopDriver uarttcp` seguido de `startDriver uarttcp` reinicia o hub pelo watchdog de hardware. Use `uartInit` para trocar o controle de fluxo sem reiniciar a ponte.

A borda direita traz os pinos de gravação, numerados de baixo para cima: Z17 = 22 (GND), Z18 = 21 (RST2), Z19 = 20 (GND), Z20 = 19 (SWCLK), Z21 = 18 (SWDIO), Z22 = 17 (3V3). Com SWDIO, SWCLK, RST2 e GND dá para recuperar o rádio com um gravador SWD.

## P2 e P3

- **P2**, abaixo de P1, está marcado **授权** (autorização). A placa semelhante RSH-GW018 DM documenta a sequência VCC, GND, RX1 e TX1. A ordem e a tensão ainda precisam de medição nesta V2.6.
- **P3**, acima do WBRG1, está marcado **测试** (teste). A referência de placa semelhante cita GND, reset, SWCLK, SWDIO e UART, mas repete a numeração dos últimos contatos. A ordem física de P3 nesta V2.6 está em aberto.

## SHA‑256 do backup original do WBRG1

O arquivo `WBRG1-firmware-original-8MB.bin` contém os 8 MiB da flash do WBRG1 desta unidade. Duas leituras independentes coincidiram. A memória do rádio Zigbee ZS3L é separada.

`1cc7751a57ae0ca369bf17c6839b3af1f3879d4e5869feb90506b0f8dc542f66`

## Referências

- [Datasheet Tuya do WBRG1](https://developer.tuya.com/cn/docs/iot/wbrg1-module-datasheet?id=Ka015vo8tfztz)
- [Datasheet Tuya do ZS3L, incluindo o modo gateway](https://developer.tuya.com/en/docs/iot/zs3l?id=K97r37j19f496)
- [UART do RTL8720D no OpenBeken 1.18.321](https://github.com/openshwprojects/OpenBK7231T_App/blob/1.18.321/src/hal/realtek/rtl8720d/hal_uart_rtl8720d.c)
- [Pinagem de referência da placa semelhante RSH-GW018 DM](https://pvvx.github.io/RSH-GW018_DM/)
