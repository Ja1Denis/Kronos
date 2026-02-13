param (
    [Parameter(Mandatory = $true)]
    [string]$Query,
    [int]$Limit = 30,
    [string]$CursorContext = "",
    [string]$CurrentFilePath = "",
    [int]$BudgetTokens = 4000,
    [string]$Mode = "budget",
    [string]$TraceFile = ""
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Url = "http://127.0.0.1:8000/query"

$StackTraceContent = $null
if ($TraceFile -and (Test-Path $TraceFile)) {
    $StackTraceContent = [string](Get-Content $TraceFile -Raw)
}

$Body = @{
    text              = $Query
    limit             = $Limit
    cursor_context    = $CursorContext
    current_file_path = $CurrentFilePath
    budget_tokens     = $BudgetTokens
    mode              = $Mode
    stack_trace       = $StackTraceContent
}

$JsonBody = $Body | ConvertTo-Json -Depth 5 -Compress

Write-Host "Sending query: '$Query'..." -ForegroundColor Cyan

try {
    $Response = Invoke-RestMethod -Uri $Url -Method Post -Body $JsonBody -ContentType "application/json" -ErrorAction Stop
}
catch {
    Write-Host "Error communicating with server: $($_.Exception.Message)" -ForegroundColor Red
    exit
}

if ($Response) {
    if ($Response.status -eq "ambiguous") {
        Write-Host "`nWarning: $($Response.message)" -ForegroundColor Yellow
        exit
    }

    if (-not $Response.context -and -not $Response.message) {
        Write-Host "No results found." -ForegroundColor Gray
    }
    else {
        if ($Response.message -and -not $Response.context) {
            Write-Host "`nInfo: $($Response.message)" -ForegroundColor Cyan
            exit
        }

        $tokens = $Response.stats.used_tokens
        $time = $Response.stats.used_latency_ms
        $method = $Response.stats.search_method
        
        Write-Host "`n=== OPTIMIZED CONTEXT (Tokens: $tokens | Time: $($time)ms) [Method: $method] ===" -ForegroundColor Magenta
        Write-Host $Response.context
        
        if ($Response.audit) {
            Write-Host "`n=== AUDIT LOG ===" -ForegroundColor DarkGray
            Write-Host $Response.audit -ForegroundColor DarkGray
        }
    }
}
else {
    Write-Host "Server returned an empty response." -ForegroundColor Red
}
