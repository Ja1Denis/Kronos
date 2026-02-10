param (
    [Parameter(Mandatory = $true)]
    [string]$Query,
    [int]$Limit = 5,
    [string]$CursorContext = "",
    [string]$CurrentFilePath = "",
    [int]$BudgetTokens = 4000,
    [string]$Mode = "budget",
    [string]$TraceFile = ""
)

# Fix encoding for Croatian characters
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Url = "http://127.0.0.1:8000/query"

try {
    $Test = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get -ErrorAction Stop
}
catch {
    Write-Host "Warning: Server check failed. Proceeding anyway..." -ForegroundColor Yellow
}

$StackTraceContent = $null
if ($TraceFile -and (Test-Path $TraceFile)) {
    $StackTraceContent = [string](Get-Content $TraceFile -Raw)
    Write-Host "Reading trace from: $TraceFile" -ForegroundColor Yellow
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
Write-Host "DEBUG JSON: $JsonBody" -ForegroundColor DarkGray

Write-Host "Sending query: '$Query'..." -ForegroundColor Cyan

try {
    $Response = Invoke-RestMethod -Uri $Url -Method Post -Body $JsonBody -ContentType "application/json"
    
    if (-not $Response.context) {
        Write-Host "No results." -ForegroundColor Gray
    }
    else {
        if ($Response.parsed_trace) {
            Write-Host "🐛 DEBUG MODE ACTIVATED (Trace Detected)" -ForegroundColor Yellow
        }
        
        Write-Host "`n=== OPTIMIZED CONTEXT (Budget: $($Response.stats.used_tokens) / $($Response.stats.global_limit) tokens) ===" -ForegroundColor Magenta
        Write-Host $Response.context
        
        Write-Host "`n=== AUDIT LOG ===" -ForegroundColor DarkGray
        Write-Host $Response.audit -ForegroundColor DarkGray
    }
}
catch {
    Write-Host "Error communicating with server." -ForegroundColor Red
    if ($_.Exception.Response) {
        Write-Host "Status Code: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
        $Stream = $_.Exception.Response.GetResponseStream()
        $Reader = New-Object System.IO.StreamReader($Stream)
        $ErrorBody = $Reader.ReadToEnd()
        Write-Host "Server Response: $ErrorBody" -ForegroundColor Red
    }
    else {
        Write-Host $_.Exception.Message
    }
}
