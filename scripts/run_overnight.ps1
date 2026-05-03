$repoRoot = "C:\Users\AlanRichardson\gatekeeper"
$pythonExe = Join-Path $repoRoot "venv\Scripts\python.exe"
$scriptPath = Join-Path $repoRoot "scripts\overnight_analysis.py"

Write-Host "Starting overnight analysis..."
& $pythonExe $scriptPath
$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host "Overnight analysis complete."
} else {
    Write-Host "Overnight analysis finished with exit code $exitCode."
}

exit $exitCode

