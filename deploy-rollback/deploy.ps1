<#
.SYNOPSIS
    Deploy a Dockerized app with automatic rollback on failure.

.DESCRIPTION
    Genericized from a script I use in production. The pattern:

      1. Upload changed files.
      2. Tag the currently-running image as the rollback target.
      3. Rebuild + restart. If the build itself fails, roll back immediately.
      4. Check startup logs for a known-good marker string. If it's not
         there within the timeout, assume the new version is broken and
         roll back automatically — no one has to notice a bad deploy at
         2am and manually intervene.

    Placeholders below (host, app dir, container/image names, log marker)
    stand in for real values — fill in your own via -RemoteHost etc. or by
    editing the defaults.

.PARAMETER RemoteHost
    SSH target, e.g. "deploy@your-server".

.PARAMETER DryRun
    Upload and syntax-check only; skip build/restart/rollback steps.
#>
param(
    [string]$RemoteHost = "deploy@your-server",
    [string]$RemoteAppDir = "/opt/yourapp",
    [string]$ImageName = "yourapp-worker",
    [string]$ContainerName = "yourapp-worker-1",
    [string]$StartupMarker = "Application startup complete",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Deploying $ImageName to $RemoteHost" -ForegroundColor Cyan

# ── Step 1: Upload changed files ──────────────────────────────────────────
Write-Host "[1/4] Uploading app files..." -ForegroundColor Yellow
scp -r (Join-Path $Root "app") "${RemoteHost}:${RemoteAppDir}/"
if ($LASTEXITCODE -ne 0) { Write-Error "scp failed"; exit 1 }
Write-Host "  uploaded OK" -ForegroundColor Green

if ($DryRun) {
    Write-Host "Dry run: stopping before build/restart." -ForegroundColor Yellow
    exit 0
}

# ── Step 2: Tag current image as rollback target ──────────────────────────
Write-Host "[2/4] Tagging current image for rollback..." -ForegroundColor Yellow
ssh $RemoteHost "docker tag ${ImageName}:latest ${ImageName}:previous 2>/dev/null || true" 2>&1 | Out-Null
Write-Host "  ${ImageName}:previous saved" -ForegroundColor Green

function Invoke-Rollback([string]$Reason) {
    Write-Host "`n  $Reason -- rolling back..." -ForegroundColor Red
    ssh $RemoteHost "docker tag ${ImageName}:previous ${ImageName}:latest && cd $RemoteAppDir && docker compose up -d $ImageName" 2>&1 | Write-Host
    Write-Error "Deploy failed. Rolled back to previous image."
    exit 1
}

# ── Step 3: Rebuild + restart ──────────────────────────────────────────────
Write-Host "[3/4] Rebuilding container..." -ForegroundColor Yellow
$ErrorActionPreference = "Continue"
ssh $RemoteHost "cd $RemoteAppDir && docker compose build $ImageName && docker compose up -d $ImageName" 2>&1 | Write-Host
$buildExit = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($buildExit -ne 0) {
    Invoke-Rollback "Build failed"
}

# ── Step 4: Post-deploy check ───────────────────────────────────────────────
Write-Host "[4/4] Checking startup logs..." -ForegroundColor Yellow
Start-Sleep -Seconds 3
$ErrorActionPreference = "Continue"
$logs = ssh $RemoteHost "docker logs $ContainerName --tail=15 2>&1"
$ErrorActionPreference = "Stop"
Write-Host $logs

if ($logs -match [regex]::Escape($StartupMarker)) {
    Write-Host "`n  Deploy successful." -ForegroundColor Green
    Write-Host "  Manual rollback if needed: docker tag ${ImageName}:previous ${ImageName}:latest && docker compose up -d $ImageName" -ForegroundColor DarkGray
} else {
    Invoke-Rollback "Startup check failed"
}
