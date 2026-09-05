param(
    [string]$Database = "energy_gpr_dw",
    [string]$Port = "5432",
    [string]$HostName = "localhost",
    [string]$User = "postgres"
)

$ErrorActionPreference = "Stop"
$env:PGHOST = $HostName
$env:PGPORT = $Port
$env:PGDATABASE = $Database
$env:PGUSER = $User

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$etlScripts = @(
    "src\etl\etl_load_time.py",
    "src\etl\etl_load_geo.py",
    "src\etl\etl_load_bridge_eu.py",
    "src\etl\etl_load_gpr.py",
    "src\etl\etl_load_import_dep.py",
    "src\etl\etl_load_energy_prices.py",
    "src\etl\etl_load_oil_stocks.py"
)

Write-Host "Database: $Database on $HostName`:$Port"
Write-Host "Run sql/schema/create_dw_schema.sql first on an empty database."

foreach ($etl in $etlScripts) {
    Write-Host "`n>>> python $etl"
    & python $etl
    if ($LASTEXITCODE -ne 0) {
        throw "ETL failed: $etl"
    }
}

Write-Host "`nETL workflow completed. Now run sql/schema/verify_final_dw.sql and the OLAP queries."
