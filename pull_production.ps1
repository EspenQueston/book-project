# Pull Production Database and Media Files to Local
# Usage: .\pull_production.ps1

$VPS_HOST = "142.93.45.77"
$VPS_USER = "root"
$VPS_APP_PATH = "/opt/duno360/app"
$LOCAL_DUMP = ".\prod_data.json"
$LOCAL_MEDIA = ".\media"

Write-Host "=== Pulling Production Data ===" -ForegroundColor Cyan

# Step 1: Dump production DB on VPS
Write-Host "[1/4] Dumping production database on VPS..." -ForegroundColor Yellow
ssh $VPS_USER@$VPS_HOST "cd $VPS_APP_PATH && source .venv/bin/activate && python manage.py dumpdata --exclude auth.permission --exclude contenttypes --indent 2 > /tmp/prod_data.json"

# Step 2: Copy dump to local
Write-Host "[2/4] Copying database dump to local..." -ForegroundColor Yellow
scp $VPS_USER@$VPS_HOST:/tmp/prod_data.json $LOCAL_DUMP

# Step 3: Load into local DB
Write-Host "[3/4] Loading data into local database..." -ForegroundColor Yellow
python manage.py loaddata $LOCAL_DUMP --ignorenonexistent

# Step 4: Copy media files
Write-Host "[4/4] Copying media files from VPS..." -ForegroundColor Yellow
if (Test-Path $LOCAL_MEDIA) {
    Remove-Item -Recurse -Force $LOCAL_MEDIA
}
scp -r $VPS_USER@$VPS_HOST:$VPS_APP_PATH/media $LOCAL_MEDIA

Write-Host "=== Done! Production data synced to local ===" -ForegroundColor Green
