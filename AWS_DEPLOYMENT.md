# AWS Deployment Guide

This guide will help you deploy the Christmas Quiz application to AWS EC2.

## Prerequisites

1. AWS Account
2. AWS CLI installed locally (optional but recommended)
3. SSH key pair for EC2 access

## Step 1: Launch EC2 Instance

1. Go to AWS Console → EC2 → Launch Instance
2. Choose **Ubuntu Server 22.04 LTS** (free tier eligible)
3. Instance type: **t2.micro** (free tier) or **t2.small** (recommended)
4. Configure Security Group with these rules:
   - **SSH (22)**: Your IP only
   - **HTTP (80)**: 0.0.0.0/0 (anywhere)
   - **HTTPS (443)**: 0.0.0.0/0 (anywhere)
   - **Custom TCP (8000)**: 0.0.0.0/0 (for backend API)
   - **Custom TCP (3000)**: 0.0.0.0/0 (for frontend - optional)
5. Create/select an SSH key pair and download it
6. Launch the instance
7. Note the **Public IPv4 address** or **Public DNS**

## Step 2: Connect to EC2 Instance

```bash
# Make key file read-only
chmod 400 your-key.pem

# Connect via SSH
ssh -i your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

## Step 3: Install Dependencies on EC2

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv -y

# Install Node.js and npm (v18 LTS)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs -y

# Install Nginx (for reverse proxy)
sudo apt install nginx -y

# Install Git
sudo apt install git -y

# Install Ollama (for AI question checking)
curl -fsSL https://ollama.com/install.sh | sh
```

## Step 4: Clone and Setup Backend

```bash
# Clone your repository
cd ~
git clone https://github.com/ogrendaniel/ChristmasQuiz.git
cd ChristmasQuiz/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install fastapi uvicorn python-dotenv bcrypt pyjwt python-multipart ollama

# Create .env file
nano .env
```

Add to .env:
```
SECRET_KEY=your-super-secret-key-change-this-in-production
OLLAMA_MODEL=llama3.1
USE_OLLAMA=true
OLLAMA_CONFIDENCE_THRESHOLD=80
```

```bash
# Pull Ollama model (in background)
ollama pull llama3.1

# Test backend
uvicorn main:app --host 0.0.0.0 --port 8000
# Press Ctrl+C to stop
```

## Step 5: Setup Backend as Service

```bash
# Create systemd service file
sudo nano /etc/systemd/system/quiz-backend.service
```

Add this content:
```ini
[Unit]
Description=Christmas Quiz Backend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/ChristmasQuiz/backend
Environment="PATH=/home/ubuntu/ChristmasQuiz/backend/venv/bin"
ExecStart=/home/ubuntu/ChristmasQuiz/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable quiz-backend
sudo systemctl start quiz-backend
sudo systemctl status quiz-backend
```

## Step 6: Setup Frontend

```bash
cd ~/ChristmasQuiz/frontend

# Install dependencies
npm install

# Update config.js with your EC2 IP
nano src/config.js
```

Update `API_URL` to:
```javascript
export const API_URL = 'http://YOUR_EC2_PUBLIC_IP:8000';
```

```bash
# Build for production
npm run build

# The build folder will be served by Nginx
```

## Step 7: Configure Nginx

```bash
# Remove default config
sudo rm /etc/nginx/sites-enabled/default

# Create new config
sudo nano /etc/nginx/sites-available/quiz
```

Add this configuration:
```nginx
server {
    listen 80;
    server_name YOUR_EC2_PUBLIC_IP;

    # Frontend
    location / {
        root /home/ubuntu/ChristmasQuiz/frontend/build;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend images
    location /images {
        proxy_pass http://localhost:8000;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/quiz /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

## Step 8: Update Frontend Config Locally

Before deploying, update your local `frontend/src/config.js`:

```javascript
export const API_URL = 'http://YOUR_EC2_PUBLIC_IP';
```

Then rebuild and copy to EC2:
```bash
# On local machine
cd frontend
npm run build

# Copy build folder to EC2
scp -i your-key.pem -r build/* ubuntu@YOUR_EC2_PUBLIC_IP:/home/ubuntu/ChristmasQuiz/frontend/build/
```

## Step 9: Optional - Setup Domain with SSL

If you have a domain name:

1. Point your domain A record to EC2 IP
2. Install Certbot for SSL:

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d yourdomain.com
```

Update `config.js` to use `https://yourdomain.com`

## Maintenance Commands

```bash
# View backend logs
sudo journalctl -u quiz-backend -f

# Restart backend
sudo systemctl restart quiz-backend

# Restart Nginx
sudo systemctl restart nginx

# Update code
cd ~/ChristmasQuiz
git pull
cd backend
source venv/bin/activate
sudo systemctl restart quiz-backend

cd ../frontend
npm run build
sudo systemctl restart nginx
```

## Troubleshooting

1. **Backend not starting**: Check logs with `sudo journalctl -u quiz-backend -f`
2. **Cannot connect**: Verify Security Group rules in AWS Console
3. **502 Bad Gateway**: Backend service might be down - check `sudo systemctl status quiz-backend`
4. **CORS errors**: Check that API_URL in config.js matches your EC2 IP/domain

## Cost Estimate

- **t2.micro** (free tier): Free for 12 months (750 hours/month)
- **t2.small**: ~$17/month
- **Data transfer**: First 100GB/month free
- **Storage**: First 30GB free

Total cost after free tier: ~$17-25/month for t2.small
