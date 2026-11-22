// Arquivo para o sistema de arquivos do OpenBeken; nao executar no Windows.
// Proposta inicial: preservar o NCP Zigbee atual e consultar sua versao.
// UART0: TX PA18, RX PA19, RTS PA16, CTS PA17.
// 115200 baud; buffer 512; sem canal indicador; controle de fluxo ligado.
startDriver uarttcp 115200 512 -1 1
