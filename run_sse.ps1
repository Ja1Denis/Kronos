$env:PYTHONPATH = $PSScriptRoot
$env:KRONOS_PORT = "8765"
Set-Location $PSScriptRoot
python -m src.mcp_server --sse --port 8765
