[CmdletBinding()]
param(
    [string]$RunId = "sdc-canary-001-v01-rehearsal-run",
    [switch]$MigrationRoundTrip
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Assert-NativeSuccess {
    param([Parameter(Mandatory = $true)][string]$Step)
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE"
    }
}

$Docker = (Get-Command docker -ErrorAction Stop).Source
$Uv = (Get-Command uv -ErrorAction Stop).Source

& $Docker version
Assert-NativeSuccess "Docker Engine preflight"
& $Docker compose config --quiet
Assert-NativeSuccess "Docker Compose configuration validation"
& $Docker compose up -d --wait
Assert-NativeSuccess "Docker Compose health wait"
& $Docker compose ps
Assert-NativeSuccess "Docker Compose health evidence"
& $Docker compose images
Assert-NativeSuccess "Docker image evidence"
& $Docker compose exec -T postgres pg_isready -U sdc -d sdc
Assert-NativeSuccess "PostgreSQL health check"
& $Docker compose exec -T temporal tctl --address temporal:7233 cluster health
Assert-NativeSuccess "Temporal health check"

& $Uv sync --frozen
Assert-NativeSuccess "uv frozen sync"
& $Uv run alembic upgrade head
Assert-NativeSuccess "Alembic upgrade head"
if ($MigrationRoundTrip) {
    & $Uv run alembic downgrade 0002
    Assert-NativeSuccess "Alembic downgrade to 0002"
    & $Uv run alembic upgrade head
    Assert-NativeSuccess "Alembic upgrade after round trip"
}
& $Uv run alembic check
Assert-NativeSuccess "Alembic check"

# The child process receives only the FakeProvider rehearsal settings. Provider credentials and
# live-authorization paths are removed without reading or printing their values.
$env:SDC_PROVIDER = "fake"
$env:SDC_TASK_QUEUE = "sdc-canary-001-v01-rehearsal"
$env:SDC_ARK_MAX_IN_FLIGHT = "1"
Remove-Item Env:SDC_ARK_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:SDC_LIVE_AUTHORIZATION_PATH -ErrorAction SilentlyContinue
Remove-Item Env:SDC_PROVIDER_CAPABILITY_PATH -ErrorAction SilentlyContinue
Remove-Item Env:SDC_PROVIDER_PRICING_PATH -ErrorAction SilentlyContinue

& $Uv run python -m sdc.canary_rehearsal `
    --run-id $RunId `
    --database-url "postgresql+asyncpg://sdc:sdc@127.0.0.1:5432/sdc" `
    --temporal-address "127.0.0.1:7233" `
    --output-root ".artifacts/canary-rehearsal" `
    --report ".artifacts/canary-rehearsal/report.json"
Assert-NativeSuccess "FakeProvider canary rehearsal"
