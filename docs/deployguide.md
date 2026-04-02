# InvSys - Complete Deployment Guide

## System Overview
InvSys is a Django-based invoice and quotation management system with Arabic language support. It uses WeasyPrint for PDF generation with Arabic fonts (Cairo and Noto Sans Arabic).

## Prerequisites
- Ubuntu 22.04 or 24.04 LTS (recommended)
- At least 2GB RAM
- 20GB+ disk space
- Root or sudo access
- Domain name (optional, for production with SSL)

---

## Step 1: Update System and Install System Packages

### 1.1 Update System
```bash
sudo apt update
sudo apt upgrade -y
```

### 1.2 Install Python and Development Tools
```bash
sudo apt install -y python3 python3-pip python3-venv python3-dev
sudo apt install -y build-essential git curl wget
```

### 1.3 Install WeasyPrint Dependencies
WeasyPrint requires several system libraries for rendering PDFs:

```bash
# Install core libraries
sudo apt install -y \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    libcairo2 \
    libcairo2-dev \
    shared-mime-info

# Install additional graphics libraries
sudo apt install -y \
    fontconfig \
    libharfbuzz-dev \
    libharfbuzz0b \
    libjpeg-dev \
    libpng-dev
```

### 1.4 Install Arabic Font Packages
Install system-level Arabic fonts for proper rendering:

```bash
# Install Arabic and multilingual font packages
sudo apt install -y \
    fonts-arabeyes \
    fonts-farsiweb \
    fonts-kacst \
    fonts-noto \
    fonts-noto-core \
    fonts-noto-ui-core \
    fonts-dejavu-core \
    fonts-liberation

# Update font cache
sudo fc-cache -fv
```

### 1.5 Verify Font Installation
```bash
# List available Arabic fonts
fc-list :lang=ar | head -10
```

---

## Step 2: Create Application User (Optional but Recommended)

For security, run the application as a non-root user:

```bash
# Create invsys user
sudo useradd -m -s /bin/bash invsys
sudo passwd invsys

# Add to sudo group (optional)
sudo usermod -aG sudo invsys

# Switch to invsys user
sudo su - invsys
```

---

## Step 3: Clone or Transfer the Application

### Option A: Clone from Git Repository
```bash
cd ~
git clone https://github.com/essyem/invsys.git
cd invsys
```

### Option B: Transfer Files via SCP
On your local machine:
```bash
# Compress the project
tar -czf invsys.tar.gz /path/to/invsys

# Transfer to new VM
scp invsys.tar.gz user@new-vm-ip:~/

# On the new VM, extract
cd ~
tar -xzf invsys.tar.gz
cd invsys
```

---

## Step 4: Set Up Python Virtual Environment

```bash
# Navigate to project directory
cd /root/invsys  # or /home/invsys/invsys if using invsys user

# Create virtual environment
python3 -m venv env-inv

# Activate virtual environment
source env-inv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

---

## Step 5: Install Python Dependencies

### 5.1 Create requirements.txt (if not present)
Create or update the requirements.txt file:

```bash
cat > requirements.txt << 'EOF'
Django==5.2.8
django-crispy-forms==2.5
crispy-bootstrap5==2025.6
gunicorn==23.0.0
weasyprint==67.0
arabic-reshaper==3.0.0
python-bidi==0.6.7
reportlab==4.4.5
Faker==38.2.0
pillow==12.0.0
EOF
```

### 5.2 Install Python Packages
```bash
pip install -r requirements.txt
```

---

## Step 6: Set Up Arabic Font Files

### 6.1 Create Fonts Directory
```bash
mkdir -p /root/invsys/fonts
cd /root/invsys/fonts
```

### 6.2 Download Cairo Fonts
```bash
# Download Cairo fonts from Google Fonts
wget https://github.com/google/fonts/raw/main/ofl/cairo/Cairo-Regular.ttf
wget https://github.com/google/fonts/raw/main/ofl/cairo/Cairo-Bold.ttf
```

### 6.3 Download Noto Sans Arabic Fonts
```bash
# Download Noto Sans Arabic fonts
wget https://github.com/google/fonts/raw/main/ofl/notosansarabic/NotoSansArabic-Regular.ttf
wget https://github.com/google/fonts/raw/main/ofl/notosansarabic/NotoSansArabic-Bold.ttf
```

### 6.4 Set Proper Permissions
```bash
chmod 644 /root/invsys/fonts/*.ttf
```

### 6.5 Verify Font Files
```bash
ls -lh /root/invsys/fonts/
# Should show:
# Cairo-Bold.ttf
# Cairo-Regular.ttf
# NotoSansArabic-Bold.ttf
# NotoSansArabic-Regular.ttf
```

---

## Step 7: Configure Django Application

### 7.1 Update Settings for Production
Edit `/root/invsys/invsys/settings.py`:

```python
# SECURITY WARNING: Change this in production!
SECRET_KEY = 'your-unique-secret-key-here'  # Generate a new one

# Set to False in production
DEBUG = False

# Update with your domain/IP
ALLOWED_HOSTS = ['your-domain.com', 'www.your-domain.com', 'your-vm-ip']

# Update CSRF trusted origins
CSRF_TRUSTED_ORIGINS = ['https://your-domain.com', 'https://www.your-domain.com']
```

### 7.2 Generate a New Secret Key
```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 7.3 Create Required Directories
```bash
cd /root/invsys

# Create directories
mkdir -p logs
mkdir -p media
mkdir -p static
mkdir -p staticfiles
mkdir -p tmp

# Set permissions
chmod 755 logs media static staticfiles tmp
```

---

## Step 8: Initialize Database

```bash
cd /root/invsys
source env-inv/bin/activate

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput
```

---

## Step 9: Test the Application

### 9.1 Test with Django Development Server
```bash
python manage.py runserver 0.0.0.0:8000
```

Visit `http://your-vm-ip:8000` in your browser. Press Ctrl+C to stop.

### 9.2 Test with Gunicorn
```bash
gunicorn invsys.wsgi:application --bind 0.0.0.0:8007
```

Visit `http://your-vm-ip:8007` in your browser. Press Ctrl+C to stop.

---

## Step 10: Set Up Gunicorn as a Systemd Service

### 10.1 Create Systemd Service File
```bash
sudo nano /etc/systemd/system/invsys.service
```

Add the following content:

```ini
[Unit]
Description=InvSys Gunicorn Daemon
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=/root/invsys
Environment="PATH=/root/invsys/env-inv/bin"
ExecStart=/root/invsys/env-inv/bin/gunicorn \
    --config /root/invsys/gunicorn_config.py \
    invsys.wsgi:application

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Note:** If using the `invsys` user instead of root, update `User=invsys`, `Group=invsys`, and all paths to `/home/invsys/invsys`.

### 10.2 Enable and Start the Service
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable invsys

# Start the service
sudo systemctl start invsys

# Check status
sudo systemctl status invsys

# View logs
sudo journalctl -u invsys -f
```

### 10.3 Useful Service Commands
```bash
# Stop the service
sudo systemctl stop invsys

# Restart the service
sudo systemctl restart invsys

# View logs
sudo tail -f /root/invsys/logs/gunicorn-error.log
sudo tail -f /root/invsys/logs/gunicorn-access.log
```

---

## Step 11: Install and Configure Nginx (Recommended)

### 11.1 Install Nginx
```bash
sudo apt install -y nginx
```

### 11.2 Create Nginx Configuration
```bash
sudo nano /etc/nginx/sites-available/invsys
```

Add the following configuration:

```nginx
upstream invsys_app {
    server 127.0.0.1:8007;
}

server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    client_max_body_size 20M;
    
    # Logging
    access_log /var/log/nginx/invsys-access.log;
    error_log /var/log/nginx/invsys-error.log;
    
    # Static files
    location /static/ {
        alias /root/invsys/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Media files
    location /media/ {
        alias /root/invsys/media/;
        expires 7d;
    }
    
    # Proxy to Gunicorn
    location / {
        proxy_pass http://invsys_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

### 11.3 Enable the Site
```bash
# Create symbolic link
sudo ln -s /etc/nginx/sites-available/invsys /etc/nginx/sites-enabled/

# Remove default site (optional)
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx

# Enable Nginx to start on boot
sudo systemctl enable nginx
```

### 11.4 Update File Permissions for Nginx
If Nginx runs as www-data user:
```bash
# Allow Nginx to access static and media files
chmod 755 /root
chmod 755 /root/invsys
chmod -R 755 /root/invsys/staticfiles
chmod -R 755 /root/invsys/media
```

**Alternative:** Run Nginx as root (less secure) or move files to /var/www/.

---

## Step 12: Configure Firewall

### 12.1 Install UFW (if not installed)
```bash
sudo apt install -y ufw
```

### 12.2 Configure Firewall Rules
```bash
# Allow SSH
sudo ufw allow ssh
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

---

## Step 13: Set Up SSL Certificate (Optional - Production Recommended)

### 13.1 Install Certbot
```bash
sudo apt install -y certbot python3-certbot-nginx
```

### 13.2 Obtain SSL Certificate
```bash
# Make sure your domain points to this VM's IP address
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

### 13.3 Auto-Renewal
Certbot automatically sets up certificate renewal. Test it:
```bash
sudo certbot renew --dry-run
```

---

## Step 14: Post-Deployment Tasks

### 14.1 Create Test Data (Optional)
```bash
cd /root/invsys
source env-inv/bin/activate
python manage.py populate_test_data
```

### 14.2 Set Up Database Backups
Create a backup script:

```bash
nano /root/backup_invsys.sh
```

Add:
```bash
#!/bin/bash
BACKUP_DIR="/root/invsys_backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
cp /root/invsys/db.sqlite3 $BACKUP_DIR/db_$DATE.sqlite3

# Backup media files
tar -czf $BACKUP_DIR/media_$DATE.tar.gz /root/invsys/media/

# Keep only last 7 days of backups
find $BACKUP_DIR -name "db_*.sqlite3" -mtime +7 -delete
find $BACKUP_DIR -name "media_*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
```

Make it executable and add to cron:
```bash
chmod +x /root/backup_invsys.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /root/backup_invsys.sh") | crontab -
```

### 14.3 Monitor System Resources
```bash
# Install htop for monitoring
sudo apt install -y htop

# Check disk space
df -h

# Check memory usage
free -h

# Check running processes
htop
```

---

## Step 15: Troubleshooting

### 15.1 Check Service Status
```bash
# Check Gunicorn
sudo systemctl status invsys
sudo journalctl -u invsys -n 50

# Check Nginx
sudo systemctl status nginx
sudo nginx -t

# Check application logs
tail -f /root/invsys/logs/gunicorn-error.log
```

### 15.2 Common Issues

**Issue: Fonts not rendering in PDFs**
```bash
# Verify fonts are installed
ls -lh /root/invsys/fonts/
fc-list :lang=ar

# Reinstall WeasyPrint dependencies
sudo apt install -y libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0
pip install --force-reinstall weasyprint
```

**Issue: Permission denied errors**
```bash
# Fix permissions
sudo chown -R root:root /root/invsys
chmod 755 /root/invsys
chmod -R 755 /root/invsys/staticfiles
chmod -R 755 /root/invsys/media
```

**Issue: 502 Bad Gateway from Nginx**
```bash
# Check if Gunicorn is running
sudo systemctl status invsys

# Check Gunicorn logs
tail -f /root/invsys/logs/gunicorn-error.log

# Check if port 8007 is listening
sudo netstat -tlnp | grep 8007
```

**Issue: Static files not loading**
```bash
# Recollect static files
cd /root/invsys
source env-inv/bin/activate
python manage.py collectstatic --noinput

# Restart services
sudo systemctl restart invsys
sudo systemctl restart nginx
```

---

## Step 16: Updating the Application

### 16.1 Pull Latest Changes
```bash
cd /root/invsys
git pull origin main  # or transfer new files via scp
```

### 16.2 Update Dependencies
```bash
source env-inv/bin/activate
pip install -r requirements.txt --upgrade
```

### 16.3 Run Migrations
```bash
python manage.py migrate
```

### 16.4 Collect Static Files
```bash
python manage.py collectstatic --noinput
```

### 16.5 Restart Services
```bash
sudo systemctl restart invsys
sudo systemctl restart nginx
```

---

## Quick Reference Commands

```bash
# Activate virtual environment
source /root/invsys/env-inv/bin/activate

# Django management commands
python manage.py migrate              # Run migrations
python manage.py createsuperuser     # Create admin user
python manage.py collectstatic       # Collect static files
python manage.py runserver 0.0.0.0:8000  # Development server

# Service management
sudo systemctl start invsys          # Start application
sudo systemctl stop invsys           # Stop application
sudo systemctl restart invsys        # Restart application
sudo systemctl status invsys         # Check status

# Logs
sudo journalctl -u invsys -f         # Follow systemd logs
tail -f /root/invsys/logs/gunicorn-error.log   # Gunicorn errors
tail -f /root/invsys/logs/gunicorn-access.log  # Gunicorn access
tail -f /var/log/nginx/invsys-error.log        # Nginx errors

# Nginx management
sudo systemctl restart nginx         # Restart Nginx
sudo nginx -t                        # Test configuration
```

---

## Security Checklist

- [ ] Change SECRET_KEY in settings.py
- [ ] Set DEBUG = False in production
- [ ] Update ALLOWED_HOSTS
- [ ] Configure firewall (UFW)
- [ ] Set up SSL certificate
- [ ] Use strong passwords for Django admin
- [ ] Regular database backups
- [ ] Keep system packages updated
- [ ] Monitor logs regularly
- [ ] Restrict SSH access (use key-based auth)

---

## Support and Maintenance

### Log Locations
- Gunicorn Error Log: `/root/invsys/logs/gunicorn-error.log`
- Gunicorn Access Log: `/root/invsys/logs/gunicorn-access.log`
- Nginx Error Log: `/var/log/nginx/invsys-error.log`
- Nginx Access Log: `/var/log/nginx/invsys-access.log`
- System Log: `journalctl -u invsys`

### Important File Locations
- Application: `/root/invsys/`
- Virtual Environment: `/root/invsys/env-inv/`
- Static Files: `/root/invsys/staticfiles/`
- Media Files: `/root/invsys/media/`
- Database: `/root/invsys/db.sqlite3`
- Arabic Fonts: `/root/invsys/fonts/`
- Systemd Service: `/etc/systemd/system/invsys.service`
- Nginx Config: `/etc/nginx/sites-available/invsys`

---

## Additional Notes

### Arabic Font Rendering
- The application uses Cairo and Noto Sans Arabic fonts
- Fonts must be available both as TTF files in `/root/invsys/fonts/` and as system fonts
- WeasyPrint uses system fonts for PDF rendering
- Use `fc-list :lang=ar` to verify Arabic fonts are installed system-wide

### Performance Tuning
- Adjust Gunicorn workers in `gunicorn_config.py` based on server resources
- Default: `workers = CPU_count * 2 + 1`
- Monitor memory usage with `free -h` and adjust as needed

### Database
- Current setup uses SQLite (suitable for small to medium deployments)
- For larger deployments, consider PostgreSQL:
  ```bash
  sudo apt install postgresql postgresql-contrib python3-psycopg2
  pip install psycopg2-binary
  # Update DATABASES in settings.py
  ```

---

**Deployment Guide Version:** 1.0  
**Last Updated:** April 2026  
**Application:** InvSys Invoice Management System
