$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$statusPath = Join-Path $taskRoot 'work\serial-capture-status.json'
$rawPath = Join-Path $taskRoot 'outputs\captura-COM12-1hora.bin'
$textPath = Join-Path $taskRoot 'outputs\captura-COM12-1hora.txt'
$started = [DateTimeOffset]::Now
$deadline = $started.AddHours(1)
$totalBytes = 0
$serial = $null
$rawFile = $null
$textFile = $null
function Save-CaptureStatus($state, $failureText) {
 [ordered]@{ state=$state; pid=$PID; port='COM12'; baud=115200; started=$started.ToString('o'); deadline=$deadline.ToString('o'); updated=[DateTimeOffset]::Now.ToString('o'); bytes=$totalBytes; error=$failureText } | ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8
}
try {
 $serial = [System.IO.Ports.SerialPort]::new('COM12',115200,[System.IO.Ports.Parity]::None,8,[System.IO.Ports.StopBits]::One)
 $serial.Handshake = [System.IO.Ports.Handshake]::None
 $serial.DtrEnable = $false
 $serial.RtsEnable = $false
 $serial.ReadTimeout = 1000
 $serial.Open()
 $rawFile = [System.IO.File]::Open($rawPath,[System.IO.FileMode]::Create,[System.IO.FileAccess]::Write,[System.IO.FileShare]::Read)
 $textFile = [System.IO.StreamWriter]::new($textPath,$false,[System.Text.UTF8Encoding]::new($false))
 $textFile.AutoFlush = $true
 $decoder = [System.Text.Encoding]::UTF8.GetDecoder()
 $buffer = [byte[]]::new(8192)
 $chars = [char[]]::new(8192)
 Save-CaptureStatus 'running' $null
 $lastStatus = [DateTimeOffset]::Now
 while ([DateTimeOffset]::Now -lt $deadline) {
  try {
   $count = $serial.Read($buffer,0,$buffer.Length)
   if ($count -gt 0) {
    $rawFile.Write($buffer,0,$count)
    $rawFile.Flush()
    $totalBytes += $count
    $charCount = $decoder.GetChars($buffer,0,$count,$chars,0,$false)
    if ($charCount -gt 0) { $textFile.Write($chars,0,$charCount) }
   }
  } catch [System.TimeoutException] { }
  if (([DateTimeOffset]::Now - $lastStatus).TotalSeconds -ge 5) {
   Save-CaptureStatus 'running' $null
   $lastStatus = [DateTimeOffset]::Now
  }
 }
 Save-CaptureStatus 'completed' $null
} catch {
 Save-CaptureStatus 'failed' $_.Exception.Message
} finally {
 if ($null -ne $textFile) { $textFile.Dispose() }
 if ($null -ne $rawFile) { $rawFile.Dispose() }
 if ($null -ne $serial) { if ($serial.IsOpen) { $serial.Close() }; $serial.Dispose() }
}
