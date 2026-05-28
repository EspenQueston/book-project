#!/bin/bash
# =============================================================================
# DEPLOY TO PRODUCTION — DUNO 360
# =============================================================================
# Usage: bash deploy_to_prod.sh
#
# This script:
#   1. Commits all changes locally
#   2. Pushes to GitHub
#   3. SSHs into the VPS
#   4. Pulls from GitHub on the VPS
#   5. Restarts the duno360.service
# =============================================================================

set -e  # Exit on any error

# ── Configuration ──────────────────────────────────────────────────────────
VPS_HOST="root@ubuntu-s-2vcpu-4gb-120gb-intel-lon1"  # Your VPS SSH address
VPS_PROJECT_PATH="/opt/duno360/app"
SERVICE_NAME="duno360.service"
BRANCH="main"  # or "master" depending on your repo

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_step() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_ok() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# ── STEP 1: Check for uncommitted changes ─────────────────────────────────
print_step "STEP 1: Checking git status"

if ! git diff --quiet || ! git diff --cached --quiet || [ -n "$(git status --porcelain)" ]; then
    print_warn "Uncommitted changes detected."
    git status --short
else
    print_warn "No local changes to commit."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi

# ── STEP 2: Add and commit ─────────────────────────────────────────────────
print_step "STEP 2: Committing changes"

git add -A

# Show what's being committed
print_ok "Files staged for commit:"
git status --short

echo
read -p "Enter commit message (or press Enter for auto-generated): " msg

if [ -z "$msg" ]; then
    msg="update: mobile UI improvements, checkout form, translations ($(date '+%Y-%m-%d %H:%M'))"
fi

git commit -m "$msg"
print_ok "Committed: $msg"

# ── STEP 3: Push to GitHub ─────────────────────────────────────────────────
print_step "STEP 3: Pushing to GitHub"

git push origin $BRANCH
print_ok "Pushed to GitHub ($BRANCH branch)"

# ── STEP 4: Deploy to VPS ──────────────────────────────────────────────────
print_step "STEP 4: Deploying to VPS"

echo "Connecting to $VPS_HOST ..."

ssh "$VPS_HOST" bash -s << 'REMOTE_SCRIPT'
    set -e
    PROJECT_PATH="/opt/duno360/app"
    SERVICE_NAME="duno360.service"

    echo ""
    echo "  [VPS] Pulling latest code..."
    cd "$PROJECT_PATH"

    # Check if this is a git repo
    if [ ! -d ".git" ]; then
        echo "  [VPS] ERROR: $PROJECT_PATH is not a git repository."
        echo "  [VPS] You may need to clone or init git first."
        exit 1
    fi

    git pull origin main || git pull origin master
    echo "  [VPS] Code pulled successfully."

    # Collect static files if needed (R2/S3 storage)
    echo ""
    echo "  [VPS] Running collectstatic..."
    source .venv/bin/activate
    python manage.py collectstatic --noinput 2>/dev/null || echo "  [VPS] collectstatic skipped or already up-to-date"

    # Restart service
    echo ""
    echo "  [VPS] Restarting $SERVICE_NAME ..."
    sudo systemctl restart "$SERVICE_NAME"
    sudo systemctl status "$SERVICE_NAME" --no-pager -l

    echo ""
    echo "  [VPS] Deployment complete!"
REMOTE_SCRIPT

print_ok "VPS deployment finished!"

# ── STEP 5: Verify ───────────────────────────────────────────────────────
print_step "STEP 5: Verification"

echo "Checking service status..."
ssh "$VPS_HOST" "sudo systemctl is-active $SERVICE_NAME" && print_ok "$SERVICE_NAME is running" || print_error "$SERVICE_NAME may have issues"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  DEPLOYMENT COMPLETE!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  GitHub:  https://github.com/EspenQueston/book-project"
echo "  Live:    https://duno360.com"
echo ""
