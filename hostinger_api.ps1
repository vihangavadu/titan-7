[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$token = "DJ4beJ10jkGde4diZkh7jjmjRndHcHGrtGxJuSF2d84e1399"
$vmId  = "1400969"
$h     = @{ Authorization = "Bearer $token"; "Content-Type" = "application/json" }

Write-Host "=== VPS Info ==="
try {
    $vps = Invoke-RestMethod -Uri "https://api.hostinger.com/v1/vps/$vmId" -Headers $h -Method GET
    $vps | ConvertTo-Json -Depth 5
} catch {
    Write-Host "VPS info failed: $_"
}

Write-Host ""
Write-Host "=== Firewall Rules ==="
try {
    $fw = Invoke-RestMethod -Uri "https://api.hostinger.com/v1/vps/$vmId/firewall" -Headers $h -Method GET
    $fw | ConvertTo-Json -Depth 5
} catch {
    Write-Host "Firewall failed: $_"
}

Write-Host ""
Write-Host "=== Remote Console / VNC ==="
try {
    $console = Invoke-RestMethod -Uri "https://api.hostinger.com/v1/vps/$vmId/console" -Headers $h -Method POST
    $console | ConvertTo-Json -Depth 5
} catch {
    Write-Host "Console failed: $_"
}

Write-Host ""
Write-Host "=== Action: Run command via API (unban IP) ==="
try {
    $body = '{"command":"fail2ban-client unban --all && echo UNBANNED"}'
    $run = Invoke-RestMethod -Uri "https://api.hostinger.com/v1/vps/$vmId/run-command" -Headers $h -Method POST -Body $body
    $run | ConvertTo-Json -Depth 5
} catch {
    Write-Host "Run-command failed: $_"
}
