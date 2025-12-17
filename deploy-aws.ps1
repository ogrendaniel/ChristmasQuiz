# AWS Deployment Script for Christmas Quiz (Windows PowerShell)
# Usage: .\deploy-aws.ps1 -EC2IP "54.123.45.67" -KeyFile "C:\path\to\key.pem"

param(
    [Parameter(Mandatory=$true)]
    [string]$EC2IP,
    
    [Parameter(Mandatory=$true)]
    [string]$KeyFile
)

$ErrorActionPreference = "Stop"
$EC2User = "ubuntu"

Write-Host "======================================"
Write-Host "Christmas Quiz - AWS Deployment Script"
Write-Host "======================================"
Write-Host ""
Write-Host "EC2 IP: $EC2IP"
Write-Host "Key File: $KeyFile"
Write-Host ""

# Test SSH connection
Write-Host "Testing SSH connection..."
$testResult = ssh -i "$KeyFile" -o ConnectTimeout=5 "$EC2User@$EC2IP" "echo 'Connection successful'" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Cannot connect to EC2 instance" -ForegroundColor Red
    Write-Host "Please check:"
    Write-Host "  1. EC2 instance is running"
    Write-Host "  2. Security Group allows SSH (port 22)"
    Write-Host "  3. Key file has correct permissions"
    exit 1
}
Write-Host "Connection successful!" -ForegroundColor Green
Write-Host ""

# Update frontend config
Write-Host "1. Updating frontend config with EC2 IP..."
$configPath = "frontend\src\config.js"
$configContent = Get-Content $configPath -Raw
$configContent = $configContent -replace "export const API_URL = '[^']*';", "export const API_URL = 'http://$EC2IP';"
Set-Content $configPath $configContent
Write-Host "   Config updated" -ForegroundColor Green
Write-Host ""

# Build frontend
Write-Host "2. Building frontend..."
Push-Location frontend
try {
    npm run build
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend build failed"
    }
    Write-Host "   Frontend built successfully" -ForegroundColor Green
}
catch {
    Write-Host "Error: $_" -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location
Write-Host ""

# Copy files to EC2
Write-Host "3. Copying files to EC2..."
Write-Host "   Creating directories..."
ssh -i "$KeyFile" "$EC2User@$EC2IP" "mkdir -p ~/ChristmasQuiz/backend ~/ChristmasQuiz/frontend/build"

Write-Host "   Copying backend files..."
scp -i "$KeyFile" -r backend\*.py "$EC2User@$EC2IP`:~/ChristmasQuiz/backend/" 2>$null
scp -i "$KeyFile" backend\requirements.txt "$EC2User@$EC2IP`:~/ChristmasQuiz/backend/" 2>$null

Write-Host "   Copying frontend build..."
scp -i "$KeyFile" -r frontend\build\* "$EC2User@$EC2IP`:~/ChristmasQuiz/frontend/build/"

Write-Host "   Files copied successfully" -ForegroundColor Green
Write-Host ""

# Setup backend on EC2
Write-Host "4. Setting up backend on EC2..."
ssh -i "$KeyFile" "$EC2User@$EC2IP" "cd ~/ChristmasQuiz/backend && if [ ! -d venv ]; then python3 -m venv venv; fi && source venv/bin/activate && pip install -r requirements.txt && if [ ! -f .env ]; then echo SECRET_KEY=\$(openssl rand -hex 32) > .env && echo OLLAMA_MODEL=llama3.1 >> .env && echo USE_OLLAMA=true >> .env && echo OLLAMA_CONFIDENCE_THRESHOLD=80 >> .env; fi && echo Backend setup complete"
Write-Host "   Backend configured" -ForegroundColor Green
Write-Host ""

# Restart services
Write-Host "5. Restarting services..."
ssh -i "$KeyFile" "$EC2User@$EC2IP" "if sudo systemctl list-units --all | grep -q quiz-backend; then sudo systemctl restart quiz-backend && echo Backend service restarted; else echo Note: Backend service not configured yet; fi; if command -v nginx > /dev/null 2>&1; then sudo systemctl restart nginx 2>/dev/null && echo Nginx restarted || echo Note: Nginx not configured yet; fi"
Write-Host ""

Write-Host "======================================"
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "======================================"
Write-Host ""
Write-Host "Access your application at: http://$EC2IP" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps (if first deployment):"
Write-Host "  1. SSH into EC2: ssh -i $KeyFile $EC2User@$EC2IP"
Write-Host "  2. Follow AWS_DEPLOYMENT.md Steps 5-7 to setup services"
Write-Host "  3. Configure Nginx as reverse proxy"
Write-Host ""
Write-Host "Useful commands:"
Write-Host "  - View backend logs: sudo journalctl -u quiz-backend -f"
Write-Host "  - Restart backend: sudo systemctl restart quiz-backend"
Write-Host "  - Restart Nginx: sudo systemctl restart nginx"
Write-Host ""

# Restore original config
git checkout frontend/src/config.js 2>$null
