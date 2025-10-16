# Fly.io Deployment Guide for WattBox

## Prerequisites

1. **Install Fly CLI**
   ```bash
   # macOS
   brew install flyctl

   # Or via script
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login to Fly.io**
   ```bash
   fly auth login
   ```

## Initial Deployment

### Step 1: Create Fly App

```bash
# This will use the fly.toml configuration
fly launch --no-deploy

# When prompted:
# - App name: wattbox-production (or choose your own)
# - Region: cdg (Paris) or choose closest to you
# - Don't add PostgreSQL (we use SQLite)
# - Don't add Redis
# - Don't deploy yet (we need to set secrets first)
```

### Step 2: Create Persistent Volume

```bash
# Create a volume for database and images (1GB free tier)
fly volumes create wattbox_data --size 1 --region cdg
```

### Step 3: Set Secrets

```bash
# Set your ESP32 device IDs (comma-separated)
fly secrets set ALLOWED_DEVICE_IDS="esp32_meter_001,esp32_meter_002"

# Set CORS origins (your production domain)
fly secrets set CORS_ORIGINS="https://wattbox.jorisdemange.fr,https://wattbox-production.fly.dev"
```

### Step 4: Deploy

```bash
fly deploy
```

### Step 5: Check Status

```bash
# View app status
fly status

# View logs
fly logs

# Open in browser
fly open
```

## Configure DNS (Route 53)

After deployment, you'll get a URL like: `wattbox-production.fly.dev`

### Add CNAME in Route 53

1. Go to AWS Console → Route 53
2. Select hosted zone: `jorisdemange.fr`
3. Create record:
   - **Record name**: `wattbox`
   - **Record type**: `CNAME`
   - **Value**: `wattbox-production.fly.dev` (your Fly.io app URL)
   - **TTL**: `300`
4. Create record

### Add Custom Domain in Fly.io

```bash
# Add your custom domain
fly certs create wattbox.jorisdemange.fr

# Check certificate status
fly certs show wattbox.jorisdemange.fr
```

Wait a few minutes for DNS to propagate and SSL certificate to be issued.

### Update CORS if needed

```bash
fly secrets set CORS_ORIGINS="https://wattbox.jorisdemange.fr"
```

## Update ESP32 Configuration

Update your ESP32 code to point to:
```cpp
const char* serverUrl = "https://wattbox.jorisdemange.fr/api/upload/device";
```

## Subsequent Deployments

### Via Git Push

```bash
git add .
git commit -m "Your changes"
git push origin main
fly deploy
```

### Or setup GitHub Actions (automatic deployment)

Create `.github/workflows/fly-deploy.yml` - see below for template.

## Useful Commands

```bash
# View logs
fly logs

# SSH into the machine
fly ssh console

# Scale machines
fly scale count 1

# Check app info
fly info

# List volumes
fly volumes list

# Check secrets
fly secrets list

# Open dashboard
fly dashboard

# Check costs
fly platform billing
```

## Troubleshooting

### App won't start
```bash
fly logs
# Check for errors in the logs
```

### Database issues
```bash
fly ssh console
ls -la /data
# Check if volume is mounted and writable
```

### OCR not working
```bash
fly ssh console
tesseract --version
# Verify Tesseract is installed
```

### Out of memory (256MB exceeded)
- Your app might be using too much memory
- Consider upgrading memory: `fly scale memory 512` (will cost ~$2/month)
- Or optimize: remove unused OCR strategies, use smaller images

## Cost Monitoring

Free tier limits:
- 3 shared-cpu-1x VMs with 256MB RAM (1 VM used)
- 3GB persistent storage (1GB volume used)
- 160GB bandwidth/month

**Current setup uses FREE tier** with auto-stop/start to stay within limits.

To check usage:
```bash
fly platform billing
```

## GitHub Actions Auto-Deploy (Optional)

Create `.github/workflows/fly-deploy.yml`:

```yaml
name: Deploy to Fly.io

on:
  push:
    branches: [main]

jobs:
  deploy:
    name: Deploy app
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: superfly/flyctl-actions/setup-flyctl@master
      - run: flyctl deploy --remote-only
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

Get your Fly.io token:
```bash
fly auth token
```

Add it to GitHub:
1. Go to your repo → Settings → Secrets and variables → Actions
2. New repository secret
3. Name: `FLY_API_TOKEN`
4. Value: (paste your token)

Now every push to `main` will auto-deploy!

## Backup Database

```bash
# SSH into machine
fly ssh console

# Create backup
sqlite3 /data/wattbox.db .dump > /tmp/backup.sql

# Exit and download
exit
fly ssh sftp get /tmp/backup.sql ./backup_$(date +%Y%m%d).sql
```

## Restore Database

```bash
# Upload backup
fly ssh sftp shell
put backup.sql /tmp/backup.sql

# SSH and restore
fly ssh console
sqlite3 /data/wattbox.db < /tmp/backup.sql
```
