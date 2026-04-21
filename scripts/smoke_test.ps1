param(
  [string]$BaseUrl = "http://127.0.0.1:8088",
  [string]$ReportDate = "2026-04-01"
)

$ErrorActionPreference = "Stop"

Write-Host "[1/3] Health check -> $BaseUrl/healthz"
$health = Invoke-RestMethod -Uri "$BaseUrl/healthz" -Method Get
$health | ConvertTo-Json -Depth 5

Write-Host "[2/3] OpenAPI sample call -> OrderProfit"
$body = @{
  offset = 0
  length = 1000
  startDate = $ReportDate
  endDate = $ReportDate
  currencyCode = "CNY"
} | ConvertTo-Json

$resp = Invoke-RestMethod -Uri "$BaseUrl/lx_openapi/basicOpen/finance/mreport/OrderProfit" -Method Post -ContentType "application/json" -Body $body
$resp | ConvertTo-Json -Depth 10

Write-Host "[3/3] Done"
