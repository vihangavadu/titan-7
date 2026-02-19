# ═══════════════════════════════════════════════════════════════════════════
# TITAN V7.0.3 — CLEANUP SCRIPT (PowerShell)
# AUTHORITY: Dva.12 | STATUS: OBLIVION_ACTIVE
# PURPOSE: Clean unnecessary files from titan-main directory
# ═══════════════════════════════════════════════════════════════════════════

Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  TITAN V7.0.3 — Cleanup Script                              ║" -ForegroundColor Cyan
Write-Host "║  Authority: Dva.12 | Status: OBLIVION_ACTIVE               ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Get initial file count and size
$initialFiles = (Get-ChildItem -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
$initialSize = (Get-ChildItem -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB

Write-Host "Initial state:"
Write-Host "  Files: $initialFiles"
Write-Host "  Size: $([math]::Round($initialSize, 2)) MB"
Write-Host ""

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 1: CLEAN BUILD ARTIFACTS
# ═══════════════════════════════════════════════════════════════════════════
Write-Host "[1/6] Cleaning build artifacts..." -ForegroundColor Blue

# Clean live-build cache
if (Test-Path "iso\.build") {
    Write-Host "  [*] Cleaning live-build cache..." -ForegroundColor Yellow
    Remove-Item -Path "iso\.build" -Recurse -Force -ErrorAction SilentlyContinue
}

if (Test-Path "iso\cache") {
    Write-Host "  [*] Cleaning package cache..." -ForegroundColor Yellow
    Remove-Item -Path "iso\cache" -Recurse -Force -ErrorAction SilentlyContinue
}

if (Test-Path "iso\chroot") {
    Write-Host "  [*] Cleaning chroot directory..." -ForegroundColor Yellow
    Remove-Item -Path "iso\chroot" -Recurse -Force -ErrorAction SilentlyContinue
}

# Clean build logs
if (Test-Path "iso\build.log") {
    Write-Host "  [*] Removing build log..." -ForegroundColor Yellow
    Remove-Item -Path "iso\build.log" -Force -ErrorAction SilentlyContinue
}

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 2: CLEAN PYTHON CACHE
# ═══════════════════════════════════════════════════════════════════════════
Write-Host "[2/6] Cleaning Python cache..." -ForegroundColor Blue

Get-ChildItem -Recurse -Directory -Name "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -File -Name "*.pyc" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -File -Name "*.pyo" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -File -Name "*.pyd" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 3: CLEAN TEMPORARY FILES
# ═════════════════════════════════════════════════════════════════════════════
Write-Host "[3/6] Cleaning temporary files..." -ForegroundColor Blue

$tempFiles = @("*.tmp", "*.temp", "*.swp", "*.swo", "*~", ".DS_Store", "Thumbs.db")
foreach ($pattern in $tempFiles) {
    Get-ChildItem -Recurse -File -Name $pattern -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
}

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 4: CLEAN LOG FILES
# ═══════════════════════════════════════════════════════════════════════════
Write-Host "[4/6] Cleaning log files..." -ForegroundColor Blue

Get-ChildItem -Recurse -File -Name "*.log" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -File -Name "*.log.*" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 5: CLEAN DEVELOPMENT ARTIFACTS
# ═════════════════════════════════════════════════════════════════════════════
Write-Host "[5/6] Cleaning development artifacts..." -ForegroundColor Blue

# Remove old ISO files
Get-ChildItem -Recurse -File -Name "*.iso" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -File -Name "*.iso.sha256" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -File -Name "*.iso.md5" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

# Remove old lucid-titan files
Get-ChildItem -Recurse -File -Name "lucid-titan*.iso*" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

# Remove test artifacts
if (Test-Path "tests\__pycache__") {
    Remove-Item -Path "tests\__pycache__" -Recurse -Force -ErrorAction SilentlyContinue
}

if (Test-Path ".coverage") {
    Remove-Item -Path ".coverage" -Force -ErrorAction SilentlyContinue
}

if (Test-Path "pytest.log") {
    Remove-Item -Path "pytest.log" -Force -ErrorAction SilentlyContinue
}

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 6: CLEAN DUPLICATE/OLD FILES
# ═══════════════════════════════════════════════════════════════════════════
Write-Host "[6/6] Checking for duplicate/old files..." -ForegroundColor Blue

$buildScripts = @("build_docker.sh", "build_docker.ps1", "build_docker.bat", "build_simple.bat", "build_direct.bat")
foreach ($script in $buildScripts) {
    if (Test-Path $script) {
        Write-Host "    Keeping: $script" -ForegroundColor Green
    }
}

# ═══════════════════════════════════════════════════════════════════════════
# FINAL RESULTS
# ═══════════════════════════════════════════════════════════════════════════
$finalFiles = (Get-ChildItem -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
$finalSize = (Get-ChildItem -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB
$filesRemoved = $initialFiles - $finalFiles

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  CLEANUP COMPLETE                                          ║" -ForegroundColor Green
Write-Host "╠══════════════════════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "║  Initial files: $initialFiles                                ║" -ForegroundColor White
Write-Host "║  Final files:   $finalFiles                                  ║" -ForegroundColor White
Write-Host "║  Files removed: $filesRemoved                                ║" -ForegroundColor White
Write-Host "║  Initial size:  $([math]::Round($initialSize, 2)) MB        ║" -ForegroundColor White
Write-Host "║  Final size:    $([math]::Round($finalSize, 2)) MB          ║" -ForegroundColor White
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

Write-Host "Essential files preserved:" -ForegroundColor Cyan
Write-Host "  ✓ Core modules (iso\config\includes.chroot\opt\titan\core\)" -ForegroundColor Green
Write-Host "  ✓ Build configuration (iso\config\)" -ForegroundColor Green
Write-Host "  ✓ Profile generator (profgen\)" -ForegroundColor Green
Write-Host "  ✓ Build scripts (build_*.sh, build_*.ps1, build_*.bat)" -ForegroundColor Green
Write-Host "  ✓ Documentation (*.md)" -ForegroundColor Green
Write-Host "  ✓ Finalization script (iso\finalize_titan.sh)" -ForegroundColor Green
Write-Host ""

Write-Host "Ready for Docker build!" -ForegroundColor Green
