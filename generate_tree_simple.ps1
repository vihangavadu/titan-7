# Generate comprehensive Titan OS repository tree
$output = @()
$output += "# TITAN OS V7.0 SINGULARITY - COMPLETE REPOSITORY TREE"
$output += ""
$output += "**Generated for AI Agent Deep Analysis**"
$output += "This tree includes every file, folder, script, and artifact in the Titan OS repository."
$output += ""
$output += "```"
$output += "titan-7/"

$fileCount = 0
$dirCount = 0

function Get-DirectoryTree {
    param(
        [string]$Path,
        [string]$Prefix = ""
    )
    
    $items = Get-ChildItem -Path $Path -Force -ErrorAction SilentlyContinue | Sort-Object {-not $_.PSIsContainer}, Name
    $count = $items.Count
    
    for ($i = 0; $i -lt $count; $i++) {
        $item = $items[$i]
        $isLast = ($i -eq $count - 1)
        $connector = if ($isLast) { "+-- " } else { "|-- " }
        $newPrefix = if ($isLast) { $Prefix + "    " } else { $Prefix + "|   " }
        
        if ($item.PSIsContainer) {
            $script:dirCount++
            $displayName = $item.Name + "/"
            $script:output += "$Prefix$connector$displayName"
            
            # Skip .git objects and logs to keep tree readable
            if ($item.Name -ne "objects" -and $item.Name -ne "logs" -or $Path -notlike "*\.git*") {
                Get-DirectoryTree -Path $item.FullName -Prefix $newPrefix
            }
        } else {
            $script:fileCount++
            $size = $item.Length
            $sizeStr = ""
            if ($size -gt 1MB) {
                $sizeStr = " ($([math]::Round($size/1MB, 1)) MB)"
            } elseif ($size -gt 1KB) {
                $sizeStr = " ($([math]::Round($size/1KB, 1)) KB)"
            } elseif ($size -gt 0) {
                $sizeStr = " ($size bytes)"
            }
            $script:output += "$Prefix$connector$($item.Name)$sizeStr"
        }
    }
}

Get-DirectoryTree -Path "."

$output += "```"
$output += ""
$output += "## Repository Statistics"
$output += "- **Total Directories:** $dirCount"
$output += "- **Total Files:** $fileCount"
$output += "- **Total Items:** $($fileCount + $dirCount)"
$output += ""
$output += "## Key Directories"
$output += "- iso/config/includes.chroot/opt/titan/ - Core Titan OS modules (73 Python modules)"
$output += "- iso/config/includes.chroot/opt/titan/apps/ - Trinity GUI applications"
$output += "- iso/config/includes.chroot/opt/titan/core/ - Core system modules"
$output += "- iso/config/includes.chroot/etc/ - System configuration files"
$output += "- scripts/ - Build and deployment scripts"
$output += "- tests/ - Test suites"
$output += "- docs/ - Documentation"
$output += ""
$output += "## Core Modules (iso/config/includes.chroot/opt/titan/core/)"
$output += "73 Python modules including:"
$output += "- Integration & orchestration: integration_bridge.py, handover_protocol.py"
$output += "- Anti-detection: fingerprint_injector.py, canvas_subpixel_shim.py, audio_hardener.py, font_sanitizer.py"
$output += "- Network: proxy_manager.py, lucid_vpn.py, network_shield_loader.py, quic_proxy.py"
$output += "- Profile generation: genesis_core.py, advanced_profile_generator.py, profile_realism_engine.py"
$output += "- AI & intelligence: cognitive_core.py, ai_intelligence_engine.py, titan_ai_operations_guard.py"
$output += "- Transaction: three_ds_strategy.py, payment_preflight.py, issuer_algo_defense.py"
$output += "- Security: kill_switch.py, forensic_monitor.py, cpuid_rdtsc_shield.py"
$output += ""
$output += "---"
$dateStr = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$output += "Generated: $dateStr"

$output | Out-File -FilePath "TITAN_OS_REPO_TREE.md" -Encoding UTF8

Write-Host "Repository tree generated: TITAN_OS_REPO_TREE.md" -ForegroundColor Green
Write-Host "  - $dirCount directories" -ForegroundColor Cyan
Write-Host "  - $fileCount files" -ForegroundColor Cyan
Write-Host "  - $($fileCount + $dirCount) total items" -ForegroundColor Cyan
