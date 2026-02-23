# ═══════════════════════════════════════════════════════════════
# TITAN V9.0 — Vast.ai GPU Training Deployment (PowerShell)
# ═══════════════════════════════════════════════════════════════
# Automates: Search → Rent → Upload → Train → Download → Destroy
#
# Usage:
#   .\deploy_vastai.ps1                    # Full auto pipeline
#   .\deploy_vastai.ps1 -OfferID 25281469 # Use specific offer
#   .\deploy_vastai.ps1 -SkipSearch        # Use cheapest auto
# ═══════════════════════════════════════════════════════════════

param(
    [string]$OfferID = "",
    [switch]$SkipSearch,
    [int]$DiskGB = 50,
    [string]$Image = "pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel"
)

$ErrorActionPreference = "Stop"

$API_KEY = "460557583433320c6f66efd5848cd43497f10cac9b4d9965377926885a24a6ff"
$HEADERS = @{ "Authorization" = "Bearer $API_KEY"; "Content-Type" = "application/json" }
$BASE_URL = "https://console.vast.ai/api/v0"
$TITAN_ROOT = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$TRAINING_DIR = Join-Path $TITAN_ROOT "training"

function Log($msg) { Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $msg" -ForegroundColor Cyan }
function Err($msg) { Write-Host "[ERROR] $msg" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host " TITAN V9.0 — Vast.ai GPU Training Deployment" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

# ═══════════════════════════════════════════════════════════════
# STEP 1: Search for cheapest GPU
# ═══════════════════════════════════════════════════════════════
if (-not $OfferID) {
    Log "Searching for cheapest GPU instance (RTX 3090+, 24GB+)..."

    $query = '{"rentable":{"eq":true},"rented":{"eq":false},"num_gpus":{"eq":1},"gpu_ram":{"gte":22000},"inet_down":{"gte":50},"reliability2":{"gte":0.9},"order":[["dph_total","asc"]],"type":"on-demand"}'
    $uri = "$BASE_URL/bundles/?q=$([uri]::EscapeDataString($query))&limit=10"

    try {
        $result = Invoke-RestMethod -Uri $uri -Headers $HEADERS -Method Get
    } catch {
        Err "Failed to search Vast.ai: $_"
    }

    if (-not $result.offers -or $result.offers.Count -eq 0) {
        Err "No suitable GPU offers found"
    }

    Write-Host ""
    Write-Host "  Top 5 cheapest offers:" -ForegroundColor Green
    Write-Host "  {0,-12} {1,-15} {2,8} {3,6} {4,20}" -f "ID","GPU","$/hr","VRAM","Location"
    Write-Host "  $('-'*65)"
    $result.offers | Select-Object -First 5 | ForEach-Object {
        Write-Host "  {0,-12} {1,-15} {2,8:N3} {3,6} {4,20}" -f $_.id, $_.gpu_name, $_.dph_total, ([math]::Round($_.gpu_ram/1024)), $_.geolocation
    }
    Write-Host ""

    # Pick the cheapest
    $offer = $result.offers[0]
    $OfferID = $offer.id
    Log "Selected: $($offer.gpu_name) at `$$([math]::Round($offer.dph_total, 3))/hr in $($offer.geolocation) (ID: $OfferID)"
} else {
    Log "Using specified offer ID: $OfferID"
}

# ═══════════════════════════════════════════════════════════════
# STEP 2: Generate SSH key if needed
# ═══════════════════════════════════════════════════════════════
$sshDir = "$env:USERPROFILE\.ssh"
$sshKey = "$sshDir\id_ed25519"
$sshPub = "$sshDir\id_ed25519.pub"

if (-not (Test-Path $sshPub)) {
    Log "Generating SSH key pair..."
    if (-not (Test-Path $sshDir)) { New-Item -ItemType Directory -Path $sshDir -Force | Out-Null }
    ssh-keygen -t ed25519 -f $sshKey -N '""' -q
    Log "SSH key generated at $sshKey"
}

# Upload SSH key to Vast.ai
$pubKeyContent = Get-Content $sshPub -Raw
Log "Uploading SSH key to Vast.ai account..."
try {
    $body = @{ "ssh_key" = $pubKeyContent.Trim() } | ConvertTo-Json
    Invoke-RestMethod -Uri "$BASE_URL/ssh/" -Headers $HEADERS -Method POST -Body $body | Out-Null
    Log "SSH key uploaded."
} catch {
    Log "SSH key upload skipped (may already exist): $($_.Exception.Message)"
}

# ═══════════════════════════════════════════════════════════════
# STEP 3: Create the instance
# ═══════════════════════════════════════════════════════════════
Log "Creating instance from offer $OfferID..."

try {
    $instance = Invoke-RestMethod -Uri "$BASE_URL/asks/$OfferID/?q={`"client_id`":`"me`",`"image`":`"$Image`",`"disk`":$DiskGB,`"ssh`":true,`"direct`":true}" -Headers $HEADERS -Method PUT
    $instanceID = $instance.new_contract
    if (-not $instanceID) {
        # Try alternate response format
        $instanceID = $instance.success
    }
    Log "Instance created! ID: $instanceID"
} catch {
    Err "Failed to create instance: $_"
}

if (-not $instanceID) {
    Err "No instance ID returned. Check Vast.ai console manually."
}

# ═══════════════════════════════════════════════════════════════
# STEP 4: Wait for instance to be ready
# ═══════════════════════════════════════════════════════════════
Log "Waiting for instance $instanceID to start..."

$maxWait = 300  # 5 minutes max
$waited = 0
$sshHost = ""
$sshPort = ""

while ($waited -lt $maxWait) {
    Start-Sleep -Seconds 10
    $waited += 10

    try {
        $info = Invoke-RestMethod -Uri "$BASE_URL/instances/$instanceID/" -Headers @{"Authorization"="Bearer $API_KEY"} -Method Get
    } catch {
        Write-Host "." -NoNewline
        continue
    }

    $status = $info.actual_status
    if ($status -eq "running") {
        $sshHost = $info.public_ipaddr
        $sshPort = $info.ssh_port
        if (-not $sshPort) { $sshPort = $info.ports."22/tcp"[0].HostPort }
        Log "Instance RUNNING! SSH: root@${sshHost}:${sshPort}"
        break
    }
    Write-Host "  Status: $status (${waited}s elapsed)..." -ForegroundColor Gray
}

if (-not $sshHost) {
    Err "Instance did not start within ${maxWait}s. Check Vast.ai console."
}

# ═══════════════════════════════════════════════════════════════
# STEP 5: Upload training files via SCP
# ═══════════════════════════════════════════════════════════════
Log "Uploading training files to instance..."

# Create a tar of the training directory (phase2 generators + vastai scripts)
$tarFile = Join-Path $env:TEMP "titan_training_upload.tar.gz"
Log "Creating upload archive..."

# Use tar to create archive
$filesToUpload = @(
    "phase2/v9_seed_data.py",
    "phase2/v9_generators_card.py",
    "phase2/v9_generators_identity.py",
    "phase2/v9_generators_strategy.py",
    "phase2/v9_generators_content.py",
    "phase2/generate_training_data_v9.py",
    "vastai/gpu_lora_finetune.py",
    "vastai/onboard.sh"
)

Push-Location $TRAINING_DIR
tar czf $tarFile $filesToUpload 2>$null
Pop-Location

Log "Archive created: $tarFile ($([math]::Round((Get-Item $tarFile).Length/1024))KB)"

# SCP upload
Log "SCP uploading to instance..."
scp -P $sshPort -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -i $sshKey $tarFile "root@${sshHost}:/workspace/upload.tar.gz"

# Extract on remote
Log "Extracting files on instance..."
ssh -p $sshPort -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -i $sshKey "root@${sshHost}" "mkdir -p /workspace/training && cd /workspace/training && tar xzf /workspace/upload.tar.gz && echo 'Files extracted OK'"

# ═══════════════════════════════════════════════════════════════
# STEP 6: Run training
# ═══════════════════════════════════════════════════════════════
Log "Starting GPU training on instance (this takes 6-12 hours)..."
Log "You can monitor with: ssh -p $sshPort root@$sshHost 'tail -f /workspace/training/logs/gpu_training.log'"

# Run onboard script in tmux so it survives disconnection
ssh -p $sshPort -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -i $sshKey "root@${sshHost}" @"
tmux new-session -d -s training 'bash /workspace/training/vastai/onboard.sh 2>&1 | tee /workspace/training/logs/full_run.log'
echo 'Training started in tmux session. Use: tmux attach -t training'
"@

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host " DEPLOYMENT COMPLETE" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host " Instance ID:  $instanceID" -ForegroundColor White
Write-Host " SSH:          ssh -p $sshPort root@$sshHost" -ForegroundColor White
Write-Host " Monitor:      ssh -p $sshPort root@$sshHost 'tmux attach -t training'" -ForegroundColor White
Write-Host " Cost:         ~`$0.076/hr" -ForegroundColor White
Write-Host ""
Write-Host " When training completes, download results:" -ForegroundColor Yellow
Write-Host "   scp -P $sshPort root@${sshHost}:/workspace/titan_v9_lora_models.tar.gz ." -ForegroundColor White
Write-Host ""
Write-Host " Then deploy to VPS:" -ForegroundColor Yellow
Write-Host "   scp titan_v9_lora_models.tar.gz root@72.62.72.48:/opt/titan/training/" -ForegroundColor White
Write-Host ""
Write-Host " DESTROY instance when done (stop billing):" -ForegroundColor Red
Write-Host "   Invoke-RestMethod -Uri '$BASE_URL/instances/$instanceID/' -Headers @{'Authorization'='Bearer $API_KEY'} -Method DELETE" -ForegroundColor White
Write-Host ""

# Save instance info for later use
$infoFile = Join-Path $TRAINING_DIR "vastai\active_instance.json"
@{
    instance_id = $instanceID
    offer_id = $OfferID
    ssh_host = $sshHost
    ssh_port = $sshPort
    ssh_key = $sshKey
    created = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    cost_per_hour = 0.076
} | ConvertTo-Json | Set-Content $infoFile

Log "Instance info saved to $infoFile"
