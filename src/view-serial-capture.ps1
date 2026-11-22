$Host.UI.RawUI.WindowTitle = 'Captura COM12 - 115200 baud'
$logPath = Join-Path (Split-Path -Parent $PSScriptRoot) 'outputs\captura-COM12-1hora.txt'
Write-Host 'CAPTURA SERIAL COM12 | 115200 baud | 8N1' -ForegroundColor Cyan
Write-Host 'Exibindo as ultimas 50 linhas e acompanhando novos dados.'
Write-Host 'Os dados continuam sendo salvos no arquivo:'
Write-Host $logPath
Write-Host 'Fechar esta janela nao interrompe a captura.' -ForegroundColor Yellow
Write-Host ''
Get-Content -LiteralPath $logPath -Encoding UTF8 -Tail 50 -Wait
