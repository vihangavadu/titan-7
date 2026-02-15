param([int]$CheckIntervalSeconds = 15, [int]$MaxRetries = 5)

$repo = "vihangavadu/titan-7"
$startTime = Get-Date
$retryCount = 0
$logFile = "build_monitor.log"

"$(Get-Date) | TITAN V7.0.3 AUTONOMOUS MONITOR STARTED" | Out-File $logFile -Append

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗"
Write-Host "║  AUTONOMOUS BUILD MONITOR — Zero Manual Prompts Required      ║"
Write-Host "╚════════════════════════════════════════════════════════════════╝"
Write-Host ""
Write-Host "Configuration:"
Write-Host "  Check Interval: $($CheckIntervalSeconds)s"
Write-Host "  Max Retries: $MaxRetries"
Write-Host "  Log: $logFile"
Write-Host ""

$keepGoing = $true

while ($keepGoing) {
    $build = $null
    
    try {
        $response = Invoke-WebRequest -Uri "https://api.github.com/repos/$repo/actions/runs?per_page=1" -ErrorAction Stop
        $data = $response.Content | ConvertFrom-Json
        if ($data.workflow_runs.Count -gt 0) {
            $build = $data.workflow_runs[0]
        }
    }
    catch {
        [void]0
    }
    
    if (-not $build) {
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Waiting for build..." -ForegroundColor Gray
        Start-Sleep -Seconds $CheckIntervalSeconds
        continue
    }
    
    $elapsed = ((Get-Date) - $startTime).TotalSeconds
    $min = [int]($elapsed / 60)
    $sec = [int]($elapsed % 60)
    
    if ($build.status -eq "in_progress") {
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] BUILD IN PROGRESS | $min`m $sec`s" -ForegroundColor Cyan
        "$(Get-Date) | IN_PROGRESS | $min`m" | Out-File $logFile -Append
    }
    elseif ($build.status -eq "completed") {
        Write-Host ""
        Write-Host "╔════════════════════════════════════════════════════════════════╗"
        Write-Host "║                  BUILD COMPLETED                              ║"
        Write-Host "╚════════════════════════════════════════════════════════════════╝"
        Write-Host ""
        Write-Host "Conclusion: $($build.conclusion)"
        Write-Host "Total Time: $min`m $sec`s"
        Write-Host "Build: https://github.com/$repo/actions/runs/$($build.id)"
        Write-Host ""
        
        if ($build.conclusion -eq "success") {
            Write-Host "✓✓✓ SUCCESS — ISO READY ✓✓✓" -ForegroundColor Green
            "$(Get-Date) | SUCCESS | ISO READY FOR DEPLOYMENT" | Out-File $logFile -Append
            $keepGoing = $false
        }
        else {
            Write-Host "[!] Build failed: $($build.conclusion)" -ForegroundColor Red
            "$(Get-Date) | FAILED | Attempting automatic retry..." | Out-File $logFile -Append
            
            if ($retryCount -lt $MaxRetries) {
                $retryCount++
                Write-Host ""
                Write-Host "Automatic Retry $retryCount of $MaxRetries..." -ForegroundColor Yellow
                
                try {
                    cd c:\Users\Administrator\Desktop\titan-main
                    git pull origin main 2>&1 | Out-Null
                    git add -A 2>&1 | Out-Null
                    git commit -m "Automatic retry $retryCount - Build recovery" 2>&1 | Out-Null
                    git push origin main 2>&1 | Out-Null
                    
                    Write-Host "✓ Retry pushed, monitoring new build..." -ForegroundColor Green
                    "$(Get-Date) | RETRY_$retryCount | Pushed and monitoring new build" | Out-File $logFile -Append
                    
                    $startTime = Get-Date
                    Start-Sleep -Seconds 5
                }
                catch {
                    Write-Host "✗ Retry failed" -ForegroundColor Red
                    $keepGoing = $false
                }
            }
            else {
                Write-Host "✗ Max retries reached. Check build logs manually." -ForegroundColor Red
                "$(Get-Date) | MAX_RETRIES | Manual intervention needed" | Out-File $logFile -Append
                $keepGoing = $false
            }
        }
    }
    
    if ($keepGoing) {
        Start-Sleep -Seconds $CheckIntervalSeconds
    }
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════"
Write-Host "Monitoring complete. Logs: $logFile"
Write-Host "═══════════════════════════════════════════════════════════════"
