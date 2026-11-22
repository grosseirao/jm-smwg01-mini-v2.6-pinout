// Physical Wi-Fi recovery on PB23.
SetButtonTimes 50 3 5
AddEventHandler OnHoldStart 55 startScript wifi-recovery.bat

// BLE scanning and ESPHome API for Home Assistant.
BTInit
delay_s 8
BTStartScan
startDriver ESPHomeAPI
