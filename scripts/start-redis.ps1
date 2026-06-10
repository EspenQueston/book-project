# Start Redis in WSL and verify it responds (requires mirrored WSL networking for 127.0.0.1 from Windows).
$ErrorActionPreference = 'Stop'

Write-Host 'Starting Redis in WSL (Ubuntu-24.04)...'
$result = wsl -d Ubuntu-24.04 -u root -- bash -lc "service redis-server start && redis-cli ping"
Write-Host $result

if ($result -notmatch 'PONG') {
    Write-Error 'Redis did not respond in WSL.'
}

Write-Host 'Redis is ready. Django should use REDIS_URL=redis://127.0.0.1:6379/1'
Write-Host 'If Windows cannot connect, run: wsl --shutdown  (once, after .wslconfig mirrored mode) then retry.'
