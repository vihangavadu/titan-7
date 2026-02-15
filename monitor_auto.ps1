$repo = 'vihangavadu/titan-7'
$startTime = Get-Date
$retryCount = 0
$logFile = 'build_monitor.log'

Write-Host ''
Write-Host '╔════════════════════════════════════════════════════════════════╗'
Write-Host '║  AUTONOMOUS BUILD MONITOR — Zero Manual Prompts Required      ║'
Write-Host '╚════════════════════════════════════════════════════════════════╝'
Write-Host ''

while ($true) {
    $build = $null
    try {
        $r = Invoke-WebRequest -Uri 'https://api.github.com/repos/$repo/actions/runs?per_page=1' -ErrorAction Stop
        $d = $r.Content | ConvertFrom-Json
        if ($d.workflow_runs.Count -gt 0) { $build = $d.workflow_runs[0] }
    } catch {}
    
    if (-not $build) {
        Write-Host ('[' + (Get-Date -Format 'HH:mm:ss') + '] Waiting...') -ForegroundColor Gray
        Start-Sleep 15
        continue
    }
    
    $elapsed = ((Get-Date) - $startTime).TotalSeconds
    $min = [int]($elapsed / 60)
    $sec = [int]($elapsed % 60)
    
    if ($build.status -eq 'in_progress') {
        $msg = '[' + (Get-Date -Format 'HH:mm:ss') + '] BUILD IN PROGRESS | ' + $min + 'm ' + $sec + 's'
        Write-Host $msg -ForegroundColor Cyan
    }
    elseif ($build.status -eq 'completed') {
        Write-Host ''
        Write-Host '╔════════════════════════════════════════════════════════════════╗'
        Write-Host '║                  BUILD COMPLETED                              ║'
        Write-Host '╚════════════════════════════════════════════════════════════════╝'
        Write-Host ''
        Write-Host ('Conclusion: ' + $build.conclusion)
        Write-Host ('Total Time: ' + $min + 'm ' + $sec + 's')
        Write-Host ''
        
        if ($build.conclusion -eq 'success') {
            Write-Host '✓✓✓ SUCCESS — ISO READY ✓✓✓' -ForegroundColor Green
            break
        }
        else {
            if ($retryCount -lt 5) {
                $retryCount++
                Write-Host ('[*] Auto-retry ' + $retryCount + ' of 5...') -ForegroundColor Yellow
                try {
                    cd c:\Users\Administrator\Desktop\titan-main
                    git pull origin main 2>&1 | Out-Null
                    git add -A 2>&1 | Out-Null
                    git commit -m ('Automatic retry ' + $retryCount) 2>&1 | Out-Null
                    git push origin main 2>&1 | Out-Null
                    Write-Host '✓ Retry pushed' -ForegroundColor Green
                    $startTime = Get-Date
                    Start-Sleep 5
                } catch {
                    Write-Host "✗ Retry failed" -ForegroundColor Red
                    break
                }
            }
            else {
                Write-Host "✗ Max retries reached" -ForegroundColor Red
                break
            }
        }
    }
    
    Start-Sleep 15
}

Write-Host ''
Write-Host '═══════════════════════════════════════════════════════════════'
Write-Host 'Monitoring complete'
Write-Host '═══════════════════════════════════════════════════════════════'
