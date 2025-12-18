# Quick Deploy Script for AWS
# Usage: .\quick-deploy.ps1

$EC2IP = "13.53.35.42"
$KeyFile = "C:\Users\danie\.ssh\julquiz.pem"
$EC2User = "ubuntu"

Write-Host "======================================"
Write-Host "Quick Deploy to AWS"
Write-Host "======================================"
Write-Host ""

# Build frontend
Write-Host "1. Building frontend..." -ForegroundColor Cyan
cd frontend
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}
cd ..
Write-Host "   Build complete!" -ForegroundColor Green
Write-Host ""

# Copy frontend build
Write-Host "2. Uploading frontend to AWS..." -ForegroundColor Cyan
scp -i "$KeyFile" -r frontend\build\* "$EC2User@$EC2IP`:~/ChristmasQuiz/frontend/build/"
Write-Host "   Upload complete!" -ForegroundColor Green

# Fix permissions
Write-Host "   Fixing permissions..." -ForegroundColor Cyan
ssh -i "$KeyFile" "$EC2User@$EC2IP" "chmod -R 755 ~/ChristmasQuiz/frontend/build"
Write-Host ""

# Copy backend files
Write-Host "3. Uploading backend to AWS..." -ForegroundColor Cyan
scp -i "$KeyFile" backend\main.py "$EC2User@$EC2IP`:~/ChristmasQuiz/backend/"
scp -i "$KeyFile" backend\answer_validator.py "$EC2User@$EC2IP`:~/ChristmasQuiz/backend/"
scp -i "$KeyFile" backend\add_sample_questions.py "$EC2User@$EC2IP`:~/ChristmasQuiz/backend/" 2>$null
Write-Host "   Upload complete!" -ForegroundColor Green
Write-Host ""

# Copy images folder
Write-Host "4. Uploading images to AWS..." -ForegroundColor Cyan
ssh -i "$KeyFile" "$EC2User@$EC2IP" "mkdir -p ~/ChristmasQuiz/backend/images"
scp -i "$KeyFile" -r backend\images\* "$EC2User@$EC2IP`:~/ChristmasQuiz/backend/images/" 2>$null
ssh -i "$KeyFile" "$EC2User@$EC2IP" "chmod -R 755 ~/ChristmasQuiz/backend/images"
Write-Host "   Upload complete!" -ForegroundColor Green
Write-Host ""

# Restart backend service
Write-Host "5. Restarting backend service..." -ForegroundColor Cyan
ssh -i "$KeyFile" "$EC2User@$EC2IP" "sudo systemctl restart quiz-backend"
Write-Host "   Service restarted!" -ForegroundColor Green
Write-Host ""

Write-Host "======================================"
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "======================================"
Write-Host ""
Write-Host "Your app is live at: http://$EC2IP" -ForegroundColor Cyan
Write-Host ""