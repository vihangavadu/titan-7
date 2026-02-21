# TITAN V7.5 - Run Script on VPS
param(
    [string]$ScriptPath = "vps_verify_real.sh",
    [string]$VPSHost = "72.62.72.48",
    [string]$VPSUser = "root",
    [string]$Password = "Xt7mKp9wRv3n.Jq2026"
)

# Read the script content
$scriptContent = Get-Content $ScriptPath -Raw

# Create SSH session using plink if available, otherwise try ssh
$plinkPath = "C:\Program Files\PuTTY\plink.exe"
$sshPath = "C:\Program Files\Git\usr\bin\ssh.exe"

if (Test-Path $plinkPath) {
    Write-Host "Using PuTTY plink..."
    $sshCmd = $plinkPath
    $sshArgs = @("-pw", $Password, "-batch", "$VPSUser@$VPSHost")
} elseif (Test-Path $sshPath) {
    Write-Host "Using Git ssh..."
    $sshCmd = $sshPath
    $sshArgs = @("-o", "StrictHostKeyChecking=no", "-o", "PasswordAuthentication=yes", "$VPSUser@$VPSHost")
} else {
    Write-Host "No SSH client found"
    exit 1
}

# Execute the script
Write-Host "Executing script on VPS..."
try {
    $result = & $sshCmd @sshArgs $scriptContent
    Write-Host "Script output:"
    Write-Host $result
} catch {
    Write-Host "Error executing script: $_"
}
