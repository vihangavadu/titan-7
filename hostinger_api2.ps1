[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$token = "zkqsTRNcHivHBLF4WeUXBk6AXnCwODC2oBMzKmUg05f4a108"
$vmId  = "1400969"

$client = New-Object System.Net.WebClient
$client.Headers.Add("Authorization", "Bearer $token")
$client.Headers.Add("Content-Type", "application/json")
$client.Headers.Add("User-Agent", "hostinger-api-mcp/1.0")
$client.Headers.Add("Accept", "application/json")

Write-Host "=== Testing API connection ==="
try {
    $resp = $client.DownloadString("https://api.hostinger.com/v1/vps")
    Write-Host "VPS list: $resp"
} catch {
    Write-Host "Error: $_"
}

Write-Host ""
Write-Host "=== Try virtual-machine endpoint ==="
$client2 = New-Object System.Net.WebClient
$client2.Headers.Add("Authorization", "Bearer $token")
$client2.Headers.Add("Content-Type", "application/json")
$client2.Headers.Add("User-Agent", "hostinger-api-mcp/1.0")
try {
    $resp2 = $client2.DownloadString("https://api.hostinger.com/v1/virtual-machine")
    Write-Host "VM list: $resp2"
} catch {
    Write-Host "Error: $_"
}

Write-Host ""
Write-Host "=== Try POST console ==="
$client3 = New-Object System.Net.WebClient
$client3.Headers.Add("Authorization", "Bearer $token")
$client3.Headers.Add("Content-Type", "application/json")
$client3.Headers.Add("User-Agent", "hostinger-api-mcp/1.0")
try {
    $resp3 = $client3.UploadString("https://api.hostinger.com/v1/vps/$vmId/console", "POST", "{}")
    Write-Host "Console: $resp3"
} catch {
    Write-Host "Console error: $_"
}
