param([switch]$Navegador)
$ErrorActionPreference = 'Stop'
$raizProyecto = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $raizProyecto
$venvPython = Join-Path $raizProyecto '.venv\Scripts\python.exe'
try {
    if (-not (Test-Path -LiteralPath $venvPython)) {
        $candidates = @()
        foreach ($name in @('python.exe', 'py.exe')) {
            $command = Get-Command $name -ErrorAction SilentlyContinue
            if ($command) { $candidates += $command.Source }
        }
        $candidates += Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
        $chosen = $null
        foreach ($candidate in $candidates | Select-Object -Unique) {
            try {
                $version = & $candidate -c "import sys; print('OK' if (3,10) <= sys.version_info[:2] <= (3,14) else 'NO')" 2>$null
                if ($LASTEXITCODE -eq 0 -and $version -eq 'OK') { $chosen = $candidate; break }
            } catch { }
        }
        if (-not $chosen) { throw 'Instala Python 3.12 desde https://www.python.org/downloads/ y vuelve a abrir iniciar.bat.' }
        Write-Host 'Preparando JembaMD por primera vez...'
        & $chosen -m venv (Join-Path $raizProyecto '.venv')
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno de Python.' }
    }
    $requirements = Join-Path $raizProyecto 'requirements.txt'
    $stamp = Join-Path $raizProyecto '.venv\jembamd-requirements.sha256'
    $hash = (Get-FileHash -LiteralPath $requirements -Algorithm SHA256).Hash
    $saved = if (Test-Path -LiteralPath $stamp) { (Get-Content -LiteralPath $stamp -Raw).Trim() } else { '' }
    if ($saved -ne $hash) {
        Write-Host 'Instalando dependencias. Se necesita internet durante esta preparacion...'
        & $venvPython -m pip install -r $requirements --disable-pip-version-check
        if ($LASTEXITCODE -ne 0) { throw 'La instalacion no termino. Revisa tu conexion y vuelve a abrir iniciar.bat.' }
        Set-Content -LiteralPath $stamp -Value $hash -Encoding ASCII
    }
    if ($Navegador) {
        & $venvPython -m streamlit run (Join-Path $raizProyecto 'src\app.py') --server.address=127.0.0.1 --server.port=8501 --server.showEmailPrompt=false --browser.gatherUsageStats=false
    } else {
        Write-Host 'Abriendo la ventana de JembaMD...'
        & $venvPython (Join-Path $raizProyecto 'src\escritorio.py')
    }
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo iniciar JembaMD. Revisa los registros en .logs.' }
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
