# Código de terceiros usado no projeto

Estes arquivos foram usados durante o trabalho, mas não são distribuídos aqui. Os repositórios de origem não declaram licença. Baixe cada um pelo link, na versão indicada.

| Arquivo | Origem | Uso no projeto |
|---|---|---|
| `drv_uart_tcp.c` | [OpenBK7231T_App 1.18.321, `src/driver/drv_uart_tcp.c`](https://github.com/openshwprojects/OpenBK7231T_App/blob/1.18.321/src/driver/drv_uart_tcp.c) | Driver `uarttcp`, a ponte TCP ↔ UART para o ZS3L, na porta 8888 |
| `hal_uart_rtl8720d.c` | [OpenBK7231T_App 1.18.321, `src/hal/realtek/rtl8720d/hal_uart_rtl8720d.c`](https://github.com/openshwprojects/OpenBK7231T_App/blob/1.18.321/src/hal/realtek/rtl8720d/hal_uart_rtl8720d.c) | Pinos da UART0 (PA16–PA19) e RTS/CTS no RTL8720D |
| `RTLNFlasher.cs` | [BK7231GUIFlashTool, `BK7231Flasher/Flashers/RTLNFlasher.cs` (commit d033bf1)](https://github.com/openshwprojects/BK7231GUIFlashTool/blob/d033bf111c/BK7231Flasher/Flashers/RTLNFlasher.cs) | Gravação e leitura do WBRG1 pela UART, inclusive em endereço escolhido (app em 0x0, LittleFS em 0x3C6000) |
| `zs3l-project/flash_zs3l.py` | Origem não registrada | Gravação do ZS3L pela ponte do OpenBeken. Fica só na cópia local |

As cópias usadas eram idênticas a essas versões, conferidas em 22/11/2026.
