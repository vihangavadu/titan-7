# CLONE AND CONFIGURE READINESS CHECK
# Titan V7.0.3 SINGULARITY - Cross-Reference Verification

Write-Host "`n=== TITAN V7.0.3 CLONE & CONFIGURE READINESS ===" -ForegroundColor Cyan
Write-Host "Authority: Dva.12 | Status: SINGULARITY" -ForegroundColor Cyan

# 1. GIT CONFIGURATION
Write-Host "`n=== 1. GIT CONFIGURATION ===" -ForegroundColor Cyan
Write-Host "Remote URL:" -NoNewline
Write-Host " $(git remote get-url origin)" -ForegroundColor Green
Write-Host "Branch:" -NoNewline
Write-Host " $(git rev-parse --abbrev-ref HEAD)" -ForegroundColor Green
Write-Host "Commit:" -NoNewline
Write-Host " $(git rev-parse --short HEAD)" -ForegroundColor Green
$status = git status --short
if ([string]::IsNullOrWhiteSpace($status)) {
    Write-Host "Working Tree:" -NoNewline
    Write-Host " CLEAN" -ForegroundColor Green
} else {
    Write-Host "Working Tree:" -NoNewline
    Write-Host " MODIFIED (see below)" -ForegroundColor Yellow
    git status --short
}

# 2. CORE FILES (from preflight_scan.py check)
Write-Host "`n=== 2. CORE MODULE FILES ===" -ForegroundColor Cyan
$coreFiles = @(
    "titan/titan_core.py",
    "titan/__init__.py",
    "titan/profile_isolation.py",
    "titan/TITAN_CORE_v5.py"
)
$corePass = 0
foreach ($f in $coreFiles) {
    if (Test-Path $f) { 
        Write-Host "[OK] $f" -ForegroundColor Green
        $corePass++
    } else { 
        Write-Host "[MISS] $f" -ForegroundColor Red
    }
}
Write-Host "Result: $corePass/$($coreFiles.Count) files present"

# 3. STEALTH KERNEL MODULE FILES
Write-Host "`n=== 3. STEALTH KERNEL & eBPF FILES ===" -ForegroundColor Cyan
$stealthFiles = @(
    "titan/hardware_shield/titan_hw.c",
    "titan/hardware_shield/dkms.conf",
    "titan/hardware_shield/Makefile",
    "titan/ebpf/network_shield.c",
    "titan/ebpf/tcp_fingerprint.c"
)
$stealthPass = 0
foreach ($f in $stealthFiles) {
    if (Test-Path $f) {
        Write-Host "[OK] $f" -ForegroundColor Green
        $stealthPass++
    } else {
        Write-Host "[MISS] $f" -ForegroundColor Red
    }
}
Write-Host "Result: $stealthPass/$($stealthFiles.Count) files present"

# 4. GENESIS ENGINE FILES
Write-Host "`n=== 4. GENESIS ENGINE FILES ===" -ForegroundColor Cyan
$genesisFiles = @(
    "profgen/__init__.py",
    "profgen/config.py",
    "profgen/gen_firefox_files.py",
    "profgen/gen_places.py",
    "profgen/gen_cookies.py",
    "profgen/gen_storage.py",
    "profgen/gen_formhistory.py"
)
$genesisPass = 0
foreach ($f in $genesisFiles) {
    if (Test-Path $f) {
        Write-Host "[OK] $f" -ForegroundColor Green
        $genesisPass++
    } else {
        Write-Host "[MISS] $f" -ForegroundColor Red
    }
}
Write-Host "Result: $genesisPass/$($genesisFiles.Count) files present"

# 5. ISO BUILD CONFIG
Write-Host "`n=== 5. ISO BUILD CONFIGURATION ===" -ForegroundColor Cyan
$isoConfigFiles = @(
    "iso/auto/config",
    "iso/config/includes.chroot/etc/nftables.conf",
    "iso/config/includes.chroot/etc/sysctl.d/99-titan-hardening.conf"
)
$isoPass = 0
foreach ($f in $isoConfigFiles) {
    if (Test-Path $f) {
        Write-Host "[OK] $f" -ForegroundColor Green
        $isoPass++
    } else {
        Write-Host "[MISS] $f" -ForegroundColor Red
    }
}
Write-Host "Result: $isoPass/$($isoConfigFiles.Count) files present"

# 6. BUILD SCRIPTS
Write-Host "`n=== 6. BUILD & PATCHING SCRIPTS ===" -ForegroundColor Cyan
$buildScripts = @(
    "scripts/titan_finality_patcher.py",
    "scripts/build_iso.sh",
    "build_final.sh",
    "finalize_titan_oblivion.sh"
)
$buildPass = 0
foreach ($f in $buildScripts) {
    if (Test-Path $f) {
        Write-Host "[OK] $f" -ForegroundColor Green
        $buildPass++
    } else {
        Write-Host "[MISS] $f" -ForegroundColor Red
    }
}
Write-Host "Result: $buildPass/$($buildScripts.Count) files present"

# 7. CONFIGURATION FILES
Write-Host "`n=== 7. CONFIGURATION FILES ===" -ForegroundColor Cyan
$configFiles = @(
    "iso/config/includes.chroot/opt/titan/config/titan.env",
    "iso/config/includes.chroot/opt/lucid-empire/requirements.txt"
)
$configPass = 0
foreach ($f in $configFiles) {
    if (Test-Path $f) {
        Write-Host "[OK] $f" -ForegroundColor Green
        $configPass++
    } else {
        Write-Host "[MISS] $f" -ForegroundColor Red
    }
}
Write-Host "Result: $configPass/$($configFiles.Count) files present"

# 8. TEST SUITE
Write-Host "`n=== 8. TEST SUITE ===" -ForegroundColor Cyan
$testFiles = @(
    "tests/test_genesis_engine.py",
    "tests/test_profgen_config.py",
    "tests/conftest.py",
    "pytest.ini"
)
$testPass = 0
foreach ($f in $testFiles) {
    if (Test-Path $f) {
        Write-Host "[OK] $f" -ForegroundColor Green
        $testPass++
    } else {
        Write-Host "[MISS] $f" -ForegroundColor Red
    }
}
Write-Host "Result: $testPass/$($testFiles.Count) files present"

# 9. CI/CD WORKFLOWS
Write-Host "`n=== 9. CI/CD WORKFLOWS ===" -ForegroundColor Cyan
$cicdFiles = @(
    ".github/workflows/build.yml",
    ".github/workflows/build-iso.yml",
    ".github/workflows/test-modules.yml"
)
$cicdPass = 0
foreach ($f in $cicdFiles) {
    if (Test-Path $f) {
        Write-Host "[OK] $f" -ForegroundColor Green
        $cicdPass++
    } else {
        Write-Host "[MISS] $f" -ForegroundColor Red
    }
}
Write-Host "Result: $cicdPass/$($cicdFiles.Count) files present"

# 10. DOCUMENTATION
Write-Host "`n=== 10. DOCUMENTATION ===" -ForegroundColor Cyan
$docFiles = @(
    "README.md",
    "BUILD_GUIDE.md",
    "TITAN_V703_SINGULARITY.md",
    "docs/QUICKSTART_V7.md",
    "docs/ARCHITECTURE.md"
)
$docPass = 0
foreach ($f in $docFiles) {
    if (Test-Path $f) {
        Write-Host "[OK] $f" -ForegroundColor Green
        $docPass++
    } else {
        Write-Host "[MISS] $f" -ForegroundColor Red
    }
}
Write-Host "Result: $docPass/$($docFiles.Count) files present"

# SUMMARY
Write-Host "`n=== CLONE & CONFIGURE READINESS SUMMARY ===" -ForegroundColor Cyan
$totalFiles = $coreFiles.Count + $stealthFiles.Count + $genesisFiles.Count + $isoConfigFiles.Count + $buildScripts.Count + $configFiles.Count + $testFiles.Count + $cicdFiles.Count + $docFiles.Count
$totalPass = $corePass + $stealthPass + $genesisPass + $isoPass + $buildPass + $configPass + $testPass + $cicdPass + $docPass

Write-Host "Critical Files Present: $totalPass/$totalFiles"
$percentage = [math]::Round(($totalPass/$totalFiles)*100, 1)
Write-Host "Completion: $percentage%"

if ($totalPass -eq $totalFiles) {
    Write-Host "`n[SUCCESS] Repository is FULLY READY for clone and configuration" -ForegroundColor Green
} elseif ($percentage -ge 95) {
    Write-Host "`n[WARNING] Repository is mostly ready (~95%+) - minor files missing" -ForegroundColor Yellow
} elseif ($percentage -ge 85) {
    Write-Host "`n[CAUTION] Repository is ready (~85%+) - some components missing" -ForegroundColor Yellow
} else {
    Write-Host "`n[CRITICAL] Repository readiness below 85% - review missing components" -ForegroundColor Red
}

Write-Host "`n=== CONFIGURATION READINESS ===" -ForegroundColor Cyan
Write-Host "Persona Config:" -NoNewline
if (Test-Path "iso/config/includes.chroot/opt/titan/state/active_profile.json") {
    Write-Host " [OK] Profile configured" -ForegroundColor Green
} else {
    Write-Host " [TEMPLATE] Use titan.env defaults or create /opt/titan/state/active_profile.json" -ForegroundColor Yellow
}

Write-Host "Proxy Configuration:" -NoNewline
$titanEnv = Get-Content "iso/config/includes.chroot/opt/titan/config/titan.env" -Raw
if ($titanEnv -match "REPLACE_WITH") {
    Write-Host " [REQUIRED] Update titan.env with proxy credentials" -ForegroundColor Yellow
} else {
    Write-Host " [OK] Configured" -ForegroundColor Green
}

Write-Host "Cloud Brain (Optional):" -NoNewline
if ($titanEnv -match "TITAN_CLOUD_URL=http://REPLACE") {
    Write-Host " [OPTIONAL] Configure vLLM if needed" -ForegroundColor Yellow
} else {
    Write-Host " [OK] Configured" -ForegroundColor Green
}

Write-Host "`n"
