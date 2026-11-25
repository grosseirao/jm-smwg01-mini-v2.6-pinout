// GPIO roles for the JM-SMWG01-MINI V2.6.
SetPinRole 25 WifiLED
SetPinChannel 25 1
SetPinRole 54 LED
SetPinChannel 54 2
SetPinRole 55 Btn
SetPinChannel 55 3

// Zigbee UART0 with RTS/CTS, using channel 2 for the TCP connection LED.
startDriver uarttcp 115200 512 2 1

// Physical Wi-Fi recovery on PB23.
SetButtonTimes 50 3 5
AddEventHandler OnHoldStart 55 startScript wifi-recovery.bat

// BLE scanning and ESPHome API for Home Assistant.
BTInit
delay_s 8
BTStartScan
startDriver ESPHomeAPI

// Zigbee UART0 as the ESPHome serial proxy port "zigbee" (needs 1.18.321-mdns6).
// ZHA reaches it through the ESPHome integration; the hub acknowledges ASH frames.
// Only one of this and uarttcp can hold the radio at a time.
startDriver ESPHomeSerial
