$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = "python"
}

& $Python -m py_compile `
    app_dash.py `
    coordinator.py `
    agents\base_agent.py `
    agents\data_source_manager.py `
    agents\data_extractor.py `
    agents\data_validator.py `
    agents\data_processor.py `
    agents\analyst.py `
    agents\report_generator.py `
    agents\query_suggestion_agent.py `
    agents\conversation_agent.py `
    connectors\data_connectors.py `
    utils\data_analysis.py `
    utils\oracle_query_validator.py `
    scripts\check_secrets.py

& $Python scripts\check_secrets.py
& $Python -m pytest
& $Python -c "import app_dash; print('OK app import')"

Write-Host "OK verifica completata"
