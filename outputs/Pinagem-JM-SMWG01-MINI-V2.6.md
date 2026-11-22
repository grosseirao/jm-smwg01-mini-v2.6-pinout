# Pinagem da JM-SMWG01-MINI V2.6

Placa identificada pela inscrição `JM-SMWG01-MINI`, revisão `V2.6`, data `2024/06/25`. O módulo branco **ZS3L (EFR32MG21)** é o rádio Zigbee. O módulo azul **WBRG1 (RTL8721CSM)** é o módulo Wi‑Fi/Bluetooth.

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

Esta é a UART interna usada pela ponte do OpenBeken. A consulta local ao ZS3L funcionou a **115200 baud com RTS/CTS** e identificou **EmberZNet 6.5.5.0, build 432**, em modo coordenador. A correspondência da tabela vem dos datasheets e do código do OpenBeken. A ponte foi testada em conjunto, sem medir a continuidade de cada trilha.

| WBRG1 | ZS3L no modo gateway | Função |
|---|---|---|
| PA18 / TX0 | PD01 / UART_RX | Dados do WBRG1 para o rádio |
| PA19 / RX0 | PD00 / UART_TX | Dados do rádio para o WBRG1 |
| PA16 / RTS0 | PA03 / UART_CTS | Controle de fluxo |
| PA17 / CTS0 | PA04 / UART_RTS | Controle de fluxo |

Os logs do firmware original identificam **PB4** como controle de boot do Zigbee. A análise do código indica **PA28** como provável reset do ZS3L. Essas duas ligações físicas ainda precisam de confirmação antes de acionar os sinais.

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
