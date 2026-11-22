// Normal operation: bridge to the ZS3L NCP WITH hardware flow control.
// The stock/community NCP builds are hw-flow; the app is silent without this.
startDriver uarttcp 115200 512 1 1
