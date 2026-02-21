# TITAN V7.5 SINGULARITY — VPS Status Check (PowerShell)
# Quick status check of TITAN OS deployment on VPS

param(
    [string]$VPSHost = "72.62.72.48",
    [string]$VPSUser = "root"
)

function Invoke-SSHCommand {
    param([string]$Command)
    
    try {
        $result = ssh "$VPSUser@$VPSHost" $Command 2>&1
        if ($LASTEXITCODE -eq 0) {
            return @{ Success = $true; Output = $result; Error = "" }
        } else {
            return @{ Success = $false; Output = ""; Error = $result }
        }
    } catch {
        return @{ Success = $false; Output = ""; Error = $_.Exception.Message }
    }
}

function Test-SSHConnection {
    Write-Host "📡 Checking SSH connection..." -ForegroundColor Cyan
    
    $result = Invoke-SSHCommand "echo 'Connected'; whoami; hostname"
    
    if ($result.Success) {
        Write-Host "✅ SSH connection successful" -ForegroundColor Green
        $lines = $result.Output -split "`n"
        Write-Host "   User: $($lines[1])" -ForegroundColor Gray
        Write-Host "   Host: $($lines[2])" -ForegroundColor Gray
        return $true
    } else {
        Write-Host "❌ SSH connection failed" -ForegroundColor Red
        Write-Host "   Error: $($result.Error)" -ForegroundColor Red
        return $false
    }
}

function Get-SystemInfo {
    Write-Host "`n🖥️ System information..." -ForegroundColor Cyan
    
    $result = Invoke-SSHCommand "uname -a; df -h / | tail -1; free -h | grep Mem"
    
    if ($result.Success) {
        $lines = $result.Output -split "`n"
        Write-Host "   Kernel: $($lines[0])" -ForegroundColor Gray
        Write-Host "   Disk: $($lines[1])" -ForegroundColor Gray
        Write-Host "   Memory: $($lines[2])" -ForegroundColor Gray
        return @{
            Kernel = $lines[0]
            Disk = $lines[1]
            Memory = $lines[2]
        }
    } else {
        Write-Host "❌ Failed to get system info" -ForegroundColor Red
        return @{}
    }
}

function Get-TitanInstallation {
    Write-Host "`n📁 TITAN installation..." -ForegroundColor Cyan
    
    $result = Invoke-SSHCommand "ls -la /opt/titan/ 2>/dev/null || echo 'Not found'"
    
    if ($result.Success -and $result.Output -notlike "*Not found*") {
        Write-Host "✅ TITAN directory exists" -ForegroundColor Green
        
        $titanFiles = @{}
        $subdirs = @("core", "apps", "config")
        
        foreach ($subdir in $subdirs) {
            $countResult = Invoke-SSHCommand "find /opt/titan/$subdir -name '*.py' 2>/dev/null | wc -l"
            if ($countResult.Success) {
                $fileCount = $countResult.Output.Trim()
                $titanFiles[$subdir] = $fileCount
                Write-Host "   $subdir/: $fileCount Python files" -ForegroundColor Gray
            }
        }
        return $titanFiles
    } else {
        Write-Host "❌ TITAN directory not found" -ForegroundColor Red
        return @{}
    }
}

function Get-ServiceStatus {
    Write-Host "`n⚙️ Services status..." -ForegroundColor Cyan
    
    $services = @("titan-backend", "titan-frontend", "titan-monitor", "nginx", "postgresql")
    $serviceStatus = @{}
    
    foreach ($service in $services) {
        $result = Invoke-SSHCommand "systemctl is-active $service 2>/dev/null || echo 'inactive'"
        $status = $result.Output.Trim()
        $serviceStatus[$service] = $status
        
        $icon = if ($status -eq "active") { "🟢" } else { "🔴" }
        Write-Host "   $icon $service`: $status" -ForegroundColor Gray
    }
    
    return $serviceStatus
}

function Test-LLMBridge {
    Write-Host "`n🧠 LLM Bridge..." -ForegroundColor Cyan
    
    $result = Invoke-SSHCommand "cd /opt/titan && python3 -c 'import sys; sys.path.insert(0, \"core\"); from ollama_bridge import is_ollama_available; print(f\"Available: {is_ollama_available()}\")' 2>/dev/null"
    
    if ($result.Success) {
        Write-Host "   ✅ LLM Bridge: $($result.Output)" -ForegroundColor Green
        return $true
    } else {
        Write-Host "   ❌ LLM Bridge: Not available" -ForegroundColor Red
        return $false
    }
}

function Test-ForensicMonitor {
    Write-Host "`n🔍 Forensic Monitor..." -ForegroundColor Cyan
    
    $result = Invoke-SSHCommand "cd /opt/titan && python3 -c 'import sys; sys.path.insert(0, \"core\"); from forensic_monitor import ForensicMonitor; print(\"Available\")' 2>/dev/null"
    
    if ($result.Success) {
        Write-Host "   ✅ Forensic Monitor: Available" -ForegroundColor Green
        return $true
    } else {
        Write-Host "   ❌ Forensic Monitor: Not available" -ForegroundColor Red
        return $false
    }
}

function Get-RecentLogs {
    Write-Host "`n📋 Recent activity..." -ForegroundColor Cyan
    
    $result = Invoke-SSHCommand "journalctl -u titan-backend --no-pager -n 3 --output=cat 2>/dev/null || echo 'No logs'"
    
    if ($result.Success -and $result.Output -and $result.Output -notlike "*No logs*") {
        Write-Host "   Recent backend logs:" -ForegroundColor Gray
        $lines = $result.Output -split "`n"
        foreach ($line in $lines[0..2]) {
            if ($line.Trim()) {
                Write-Host "     $line" -ForegroundColor DarkGray
            }
        }
    } else {
        Write-Host "   No recent logs found" -ForegroundColor Gray
    }
}

function New-StatusSummary {
    param(
        [bool]$ConnectionOK,
        [hashtable]$TitanFiles,
        [hashtable]$ServiceStatus,
        [bool]$LLMWorking,
        [bool]$ForensicWorking
    )
    
    Write-Host "`n📊 Status Summary:" -ForegroundColor Cyan
    
    Write-Host "   Connection: $(if ($ConnectionOK) { '✅' } else { '❌' })" -ForegroundColor $(if ($ConnectionOK) { 'Green' } else { 'Red' })
    Write-Host "   TITAN Installed: $(if ($TitanFiles.Count -gt 0) { '✅' } else { '❌' })" -ForegroundColor $(if ($TitanFiles.Count -gt 0) { 'Green' } else { 'Red' })
    
    $activeServices = ($ServiceStatus.Values | Where-Object { $_ -eq "active" }).Count
    Write-Host "   Active Services: $activeServices/$($ServiceStatus.Count)" -ForegroundColor $(if ($activeServices -ge 3) { 'Green' } else { 'Yellow' })
    
    Write-Host "   LLM Bridge: $(if ($LLMWorking) { '✅' } else { '❌' })" -ForegroundColor $(if ($LLMWorking) { 'Green' } else { 'Red' })
    Write-Host "   Forensic Monitor: $(if ($ForensicWorking) { '✅' } else { '❌' })" -ForegroundColor $(if ($ForensicWorking) { 'Green' } else { 'Red' })
    
    # Calculate health score
    $healthScore = @($ConnectionOK, ($TitanFiles.Count -gt 0), $LLMWorking, $ForensicWorking).Where({$_}).Count
    
    $health = switch ($healthScore) {
        4 { "🟢 EXCELLENT" }
        3 { "🟡 GOOD" }
        2 { "🟠 FAIR" }
        default { "🔴 NEEDS ATTENTION" }
    }
    
    Write-Host "`n🏥 Overall Health: $health" -ForegroundColor $(switch ($healthScore) {
        4 { 'Green' }
        3 { 'Yellow' }
        2 { 'Orange' }
        default { 'Red' }
    })
    
    return @{
        HealthScore = $healthScore
        Health = $health
        ConnectionOK = $ConnectionOK
        TitanInstalled = $TitanFiles.Count -gt 0
        ActiveServices = $activeServices
        LLMWorking = $LLMWorking
        ForensicWorking = $ForensicWorking
    }
}

# Main execution
Write-Host "🔍 TITAN V7.5 VPS Status Check" -ForegroundColor Cyan
Write-Host "=" * 50 -ForegroundColor Gray

$status = @{
    Timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
    VPSHost = $VPSHost
}

# Check SSH connection first
$connectionOK = Test-SSHConnection
$status.ConnectionOK = $connectionOK

if (-not $connectionOK) {
    Write-Host "`n❌ Cannot proceed without SSH connection" -ForegroundColor Red
    exit 1
}

# Run all checks
$status.SystemInfo = Get-SystemInfo
$status.TitanFiles = Get-TitanInstallation
$status.ServiceStatus = Get-ServiceStatus
$status.LLMWorking = Test-LLMBridge
$status.ForensicWorking = Test-ForensicMonitor
Get-RecentLogs

# Generate summary
$summary = New-StatusSummary -ConnectionOK $connectionOK -TitanFiles $status.TitanFiles -ServiceStatus $status.ServiceStatus -LLMWorking $status.LLMWorking -ForensicWorking $status.ForensicWorking

# Save status report
$reportPath = "vps_status_report.json"
$status | ConvertTo-Json -Depth 3 | Out-File -FilePath $reportPath
Write-Host "`n📄 Status report saved to: $reportPath" -ForegroundColor Cyan

# Recommendations
Write-Host "`n💡 Recommendations:" -ForegroundColor Cyan
if (-not $status.TitanFiles) {
    Write-Host "   • Deploy TITAN codebase to VPS using deploy_to_vps.py" -ForegroundColor Yellow
}
if ($summary.ActiveServices -lt 3) {
    Write-Host "   • Check and restart TITAN services" -ForegroundColor Yellow
}
if (-not $status.LLMWorking) {
    Write-Host "   • Install Python dependencies for LLM bridge" -ForegroundColor Yellow
}
if (-not $status.ForensicWorking) {
    Write-Host "   • Verify forensic monitor installation" -ForegroundColor Yellow
}

Write-Host "`n🎉 Status check completed!" -ForegroundColor Green
