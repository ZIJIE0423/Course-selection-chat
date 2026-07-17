param(
    [switch]$SkipSync
)

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $projectRoot

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required. Install uv and run this script again."
}

$databaseFile = Join-Path $projectRoot "demo_course_db.sqlite"
$databaseUrlPath = $databaseFile.Replace('\', '/')
$env:MYSQL_URL = "sqlite:///$databaseUrlPath"
$env:LLM_PROVIDER = "none"
$env:FEATURE_COURSE_PLANNING = "true"
$env:FEATURE_ACADEMIC_HISTORY = "true"
$env:FEATURE_COURSE_FEEDBACK = "false"
$env:FEATURE_STUDENT_REVIEW_RAG = "false"

if (-not $SkipSync) {
    uv sync --frozen
    if ($LASTEXITCODE -ne 0) { throw "Dependency sync failed" }
}

uv run python -m app.scripts.seed_demo
if ($LASTEXITCODE -ne 0) { throw "Demo data initialization failed" }

Write-Host ""
Write-Host "WeOUC Demo is starting..." -ForegroundColor Cyan
Write-Host "Open: http://127.0.0.1:8000/prototype/" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the service." -ForegroundColor DarkGray
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
