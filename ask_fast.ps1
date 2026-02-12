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

$Job = Start-Job -ScriptBlock {
    param($Url, $JsonBody)
    try {
        return Invoke-RestMethod -Uri $Url -Method Post -Body $JsonBody -ContentType "application/json" -ErrorAction Stop
    }
    catch {
        throw $_
    }
} -ArgumentList $Url, $JsonBody

$StartTime = [System.Diagnostics.Stopwatch]::StartNew()
$Spinner = @('|', '/', '-', '\')
$i = 0

while ($Job.State -eq 'Running') {
    $Elapsed = [math]::Round($StartTime.Elapsed.TotalSeconds, 1)
    # Koristimo jednostavan format bez specijalnih znakova unutar navodnika koji bi mogli zbuniti parser
    $Msg = "Thinking... " + $Spinner[$i % 4] + " [" + $Elapsed + "s]"
    Write-Host -NoNewline ("`r" + $Msg) 
    Start-Sleep -Milliseconds 100
    $i++
}

Write-Host ""
$Response = Receive-Job -Job $Job
$JobError = $Job.ChildJobs[0].Error

if ($JobError) {
    Write-Host "Error communicating with server." -ForegroundColor Red
    Write-Host $JobError[0].Exception.Message -ForegroundColor Red
    Remove-Job $Job
    exit
}

Remove-Job $Job

if ($Response) {
    if (-not $Response.context) {
        Write-Host "No results found." -ForegroundColor Gray
    }
    else {
        if ($Response.parsed_trace) {
            Write-Host "DEBUG MODE ACTIVATED" -ForegroundColor Yellow
        }
        
        $MethodStr = if ($Response.stats.search_method) { " [Method: " + $Response.stats.search_method + "]" } else { "" }
        Write-Host ("`n=== OPTIMIZED CONTEXT (Tokens: " + $Response.stats.used_tokens + " | Time: " + $Response.stats.used_latency_ms + "ms)" + $MethodStr + " ===") -ForegroundColor Magenta
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
