# Ollama Setup & Deployment Guide

## Quick Start (5 minutes)

### Step 1: Install Ollama

**Windows**:
1. Visit https://ollama.ai/download
2. Download Windows installer
3. Run installer and follow prompts
4. Ollama will start automatically

**macOS**:
1. Visit https://ollama.ai/download
2. Download macOS app
3. Run and add to Applications
4. Start from Applications folder

**Linux**:
```bash
curl https://ollama.ai/install.sh | sh
```

### Step 2: Pull Gemma 2 Model

```bash
# Open terminal/command prompt and run:
ollama pull gemma2:7b
```

This downloads ~4-5 GB. Takes 5-10 minutes depending on connection.

### Step 3: Verify Setup

```bash
# Check available models
ollama list

# Should output:
# NAME            ID              SIZE    MODIFIED
# gemma2:7b       2a0e9872b5ae    5.2GB   2 minutes ago

# Check API is working
curl http://localhost:11434/api/tags
```

### Step 4: Configure PC Worker

```bash
cd pc_worker

# Copy environment template
cp .env.example .env

# Edit .env (change Supabase credentials only)
# Leave Ollama settings as default
```

### Step 5: Start Processing

```bash
# Terminal 1: Start Ollama server
ollama serve

# Terminal 2: Start PC Worker
cd pc_worker
python main_worker.py
```

Done! PC Worker will now summarize meetings automatically.

---

## Detailed Setup Guide

### System Requirements

**Minimum (Gemma 2 7B)**:
- CPU: 4-core processor
- RAM: 8 GB (at least)
- VRAM: 4-6 GB (GPU) OR 8+ GB (CPU)
- Disk: 10 GB free (model + temp files)

**Recommended (Gemma 2 7B)**:
- CPU: 8-core processor
- RAM: 16 GB
- VRAM: 8 GB (RTX 3060 or better)
- Disk: 20 GB SSD

**For 27B Model**:
- VRAM: 16-20 GB (RTX 4090 or A100)
- RAM: 32 GB
- Disk: 30 GB SSD

### Installation by OS

#### Windows Detailed Setup

**Option A: Using Installer (Recommended)**
1. Download from https://ollama.ai/download
2. Run `OllamaSetup.exe`
3. Choose installation directory
4. Accept firewall prompt
5. Ollama starts automatically
6. Look for Ollama icon in system tray

**Option B: Manual Setup**
```bash
# Download ollama-windows.exe
# Save to C:\Program Files\Ollama\

# Add to PATH environment variable
# System Properties → Environment Variables → Path → Add C:\Program Files\Ollama

# Test installation
ollama --version
```

**Verify Service Running**:
```bash
# Check if running on port 11434
netstat -an | findstr :11434

# Should show:
# TCP    127.0.0.1:11434        LISTENING
```

#### macOS Detailed Setup

**Using Installer**:
1. Download from https://ollama.ai/download
2. Mount .dmg file
3. Drag Ollama to Applications
4. Open Applications → Ollama
5. Allow in security prompt

**Via Homebrew**:
```bash
brew install ollama
brew services start ollama
```

**Verify Service**:
```bash
ps aux | grep ollama
# Should show ollama process

curl http://localhost:11434/api/tags
# Should return JSON
```

#### Linux Detailed Setup

**Ubuntu/Debian**:
```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Start service
sudo systemctl start ollama
sudo systemctl enable ollama  # Auto-start on boot

# Check status
sudo systemctl status ollama
```

**Other Distributions**:
```bash
# Install manually
curl https://ollama.ai/install.sh | sh

# Or download directly
wget https://ollama.ai/download/ollama-linux-x86_64.tgz
tar -xzf ollama-linux-x86_64.tgz
./ollama/bin/ollama serve
```

### Model Installation

#### Download Gemma 2 7B

```bash
ollama pull gemma2:7b
```

Expected output:
```
pulling manifest
pulling bbe438014d6e
[==========================>] 100% 5.2 GB

verifying sha256 digest
writing manifest
removing any unused layers
success
```

#### Download Gemma 2 27B (Optional)

```bash
ollama pull gemma2:27b
```

**Warning**: 16 GB download, requires 20+ GB VRAM

#### View Downloaded Models

```bash
ollama list
```

Output:
```
NAME            ID              SIZE    MODIFIED
gemma2:7b       2a0e9872b5ae    5.2GB   2 minutes ago
gemma2:27b      ... (if pulled)
```

### Configuration Files

#### Ollama Configuration

**Location**:
- Windows: `%APPDATA%\Ollama\`
- macOS: `~/.ollama/`
- Linux: `~/.ollama/`

**Key Files**:
- `Modelfile` - Custom model definitions
- `ollama.env` - Environment variables
- `logs/server.log` - Server logs

#### PC Worker Configuration

**Template**: `pc_worker/.env.example`

**Required Settings**:
```env
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJ...

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma2:7b
SUMMARIZATION_ENABLED=true
```

**Optional Tuning**:
```env
SUMMARIZATION_TIMEOUT=300      # Increase for 27B model
CHUNK_SIZE=4000               # Decrease for faster processing
SUMMARIZATION_MAX_RETRIES=3
```

### Testing Installation

#### Test Ollama API

```bash
# Test model is accessible
curl -X POST http://localhost:11434/api/generate \
  -d '{
    "model": "gemma2:7b",
    "prompt": "Hello, how are you?",
    "stream": false
  }'

# Should return JSON with response
```

#### Test PC Worker

```bash
# In pc_worker directory
python -c "
from summarizer import get_summarizer
import asyncio

async def test():
    s = get_summarizer()
    health = await s.health_check()
    print(f'Ollama Health Check: {health}')

asyncio.run(test())
"
```

Expected output:
```
Ollama Health Check: True
```

### Performance Tuning

#### Optimize for Speed

```env
# Use 7B model
OLLAMA_MODEL=gemma2:7b

# Reduce chunk size for faster processing
CHUNK_SIZE=3000

# Reduce timeout slightly
SUMMARIZATION_TIMEOUT=180
```

#### Optimize for Quality

```env
# Use 27B model (if VRAM available)
OLLAMA_MODEL=gemma2:27b

# Larger chunks for more context
CHUNK_SIZE=5000

# Increase timeout for longer processing
SUMMARIZATION_TIMEOUT=600
```

#### GPU Optimization

**NVIDIA CUDA**:
```bash
# Check GPU availability
nvidia-smi

# Install CUDA toolkit
# https://developer.nvidia.com/cuda-11-8-0-download-archive

# Verify Ollama uses GPU
ollama serve
# Look for: "loaded model in X.XXms (on GPU)"
```

**AMD ROCm**:
```bash
# Install ROCm support
# https://rocmdocs.amd.com/en/docs-5.7.1/deploy/linux/

# Configure Ollama
export CUDA_VISIBLE_DEVICES=0  # GPU index
ollama serve
```

**Apple Metal (macOS)**:
Ollama detects Metal automatically. Check logs:
```
grep "loaded model" ~/.ollama/logs/server.log
```

### Memory Management

#### Monitor Ollama Memory

**Windows**:
```bash
# Task Manager → Performance → CPU, Memory, GPU
# Look for ollama.exe process
```

**macOS**:
```bash
# Activity Monitor → Memory tab
# Search for ollama
```

**Linux**:
```bash
# Monitor in real-time
watch -n 1 'ps aux | grep ollama'

# Or using nvidia-smi
nvidia-smi -l 1  # Update every 1 second
```

#### Reduce Memory Usage

1. Use 7B instead of 27B model
2. Reduce `CHUNK_SIZE` in config
3. Lower `MAX_CONCURRENT_JOBS` to 1
4. Unload other heavy applications

#### Prevent Out of Memory

```bash
# Set maximum context size
ollama pull gemma2:7b --context-length 2048

# Or limit via environment
export OLLAMA_MAX_VRAM=6000000000  # 6GB in bytes
ollama serve
```

### Docker Deployment (Optional)

#### Docker Installation

```bash
# Install Docker Desktop
# https://www.docker.com/products/docker-desktop

# Or via package manager (Linux)
sudo apt-get install docker.io
```

#### Run Ollama in Docker

```bash
# Pull Ollama Docker image
docker pull ollama/ollama

# Run with GPU support (NVIDIA)
docker run --gpus all -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama

# Run on CPU only
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama

# Pull model inside container
docker exec ollama ollama pull gemma2:7b

# Check running
docker ps
docker logs ollama
```

#### Docker Compose (Recommended for Production)

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  ollama:
    image: ollama/ollama:latest
    container_name: ollama-server
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    environment:
      - OLLAMA_MAX_VRAM=6000000000  # 6GB
    restart: unless-stopped

  pc-worker:
    build: ./pc_worker
    container_name: meeting-pc-worker
    depends_on:
      - ollama
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}
      - LOG_LEVEL=INFO
    volumes:
      - ./pc_worker/logs:/app/logs
    restart: unless-stopped

volumes:
  ollama-data:
```

Start services:
```bash
docker-compose up -d
docker-compose logs -f pc-worker
```

### Troubleshooting

#### Issue: Port Already in Use

```bash
# Check what's using port 11434
netstat -an | findstr :11434  # Windows
lsof -i :11434                # macOS/Linux

# Change port in .env
OLLAMA_BASE_URL=http://localhost:11435

# Restart Ollama on different port
ollama serve --port 11435
```

#### Issue: Model Download Stuck

```bash
# Kill Ollama process
# pkill ollama

# Remove partial model
ollama rm gemma2:7b

# Retry download
ollama pull gemma2:7b
```

#### Issue: "Model not found"

```bash
# List available models
ollama list

# If empty, pull again
ollama pull gemma2:7b

# Verify model file
ls ~/.ollama/models/manifests/registry.ollama.ai/library/
```

#### Issue: GPU Not Being Used

```bash
# Check if GPU supported
nvidia-smi  # Should show GPU info

# Verify Ollama sees GPU
ollama serve
# Look for: "Fri Dec 13 ... loaded model in XXms (on GPU)"

# If not using GPU
# - Install NVIDIA CUDA/cuDNN
# - Check Ollama version (update if old)
# - Restart Ollama
```

#### Issue: Worker Not Connecting to Ollama

```bash
# Test connection manually
curl http://localhost:11434/api/tags

# If fails:
# 1. Ensure Ollama is running
# 2. Check OLLAMA_BASE_URL in .env
# 3. Check firewall settings
# 4. Verify port 11434 is not blocked
```

### Health Checks

#### Automated Health Monitoring

PC Worker automatically checks Ollama health every time it processes a meeting. Check logs:

```bash
# Watch logs for health checks
tail -f logs/pc_worker.log | grep -i ollama

# Should show:
# ... health check passed. Model gemma2:7b available
```

#### Manual Health Check

```bash
# API check
curl http://localhost:11434/api/tags

# Model check
curl http://localhost:11434/api/tags | grep gemma2

# Status check
ollama list
```

### Monitoring & Maintenance

#### Regular Maintenance

```bash
# Weekly: Check logs for errors
tail -100 ~/.ollama/logs/server.log | grep -i error

# Monthly: Update models
ollama pull gemma2:7b

# Quarterly: Prune unused models
ollama rm <model-name>  # Remove old versions
```

#### Performance Monitoring

```bash
# Real-time monitoring
# Watch Ollama response times in logs

# Check average processing time
grep "loading model" ~/.ollama/logs/server.log | tail -20
```

### Backup & Recovery

#### Backup Models

```bash
# Backup model data
# Windows: Copy C:\Users\<USER>\AppData\Roaming\Ollama\models
# macOS/Linux: Copy ~/.ollama/models

# Or use tar (Linux/macOS)
tar -czf ollama-backup.tar.gz ~/.ollama/models
```

#### Recovery

```bash
# Restore from backup
# Copy models back to ~/.ollama/models

# Verify
ollama list
```

---

## Production Checklist

- [ ] Ollama installed and running
- [ ] Gemma 2 7B model pulled successfully
- [ ] API accessible at http://localhost:11434
- [ ] GPU properly detected (if available)
- [ ] .env configured with correct credentials
- [ ] Supabase connection verified
- [ ] PC Worker test run successful
- [ ] Logs show "health check passed"
- [ ] Sample meeting processed successfully
- [ ] Summary generated and saved to Supabase
- [ ] Auto-start configured (systemctl/launchd/Task Scheduler)

---

## Support & Resources

- **Ollama Official**: https://ollama.ai
- **Model Library**: https://ollama.ai/library
- **Issues**: https://github.com/ollama/ollama/issues
- **Discord Community**: https://discord.gg/ollama

---

## License

This guide is part of the Meeting Minutes project.
