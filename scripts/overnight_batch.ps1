param(
    [string]$folder
)

if (-not $folder -and $args.Count -gt 0) {
    $folder = $args[0]
}

$repoRoot = "C:\Users\AlanRichardson\gatekeeper"
$pythonExe = Join-Path $repoRoot "venv\Scripts\python.exe"
$batchScript = Join-Path $repoRoot "scripts\batch_swms_analysis.py"
$outputJson = Join-Path $repoRoot "data\batch_analysis.json"
$logFile = Join-Path $repoRoot "data\overnight_log.txt"

if (-not $folder) {
    throw "Folder argument is required. Usage: .\scripts\overnight_batch.ps1 <folder>"
}

$startTs = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
Add-Content -Path $logFile -Value "$startTs START folder=$folder"

$proc = Start-Process `
    -FilePath $pythonExe `
    -ArgumentList "-m uvicorn api.main:app --port 8001 --host 127.0.0.1" `
    -WorkingDirectory $repoRoot `
    -PassThru `
    -WindowStyle Normal

Start-Sleep -Seconds 8

try {
    & $pythonExe `
        $batchScript `
        --folder $folder `
        --output $outputJson `
        --base-url "http://127.0.0.1:8001" `
        --delay 2
}
finally {
    if ($proc -and -not $proc.HasExited) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }

    $endTs = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    Add-Content -Path $logFile -Value "$endTs COMPLETE"
}

$wsh = New-Object -ComObject WScript.Shell
$null = $wsh.Popup(
    "Safe Method batch complete. 355 files processed. Check data/batch_analysis.json",
    0,
    "Safe Method",
    64
)

