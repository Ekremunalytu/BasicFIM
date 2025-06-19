# FIM System Installation Guide

## Prerequisites

### System Requirements

- **Operating System**: Linux, macOS, or Windows with WSL2
- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher
- **Memory**: Minimum 2GB RAM available for containers
- **Disk Space**: Minimum 1GB free space

### Software Installation

#### Installing Docker

**Linux (Ubuntu/Debian):**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

**macOS:**
```bash
# Install Docker Desktop from https://docker.com/products/docker-desktop
# Or using Homebrew:
brew install --cask docker
```

**Windows:**
Install Docker Desktop from https://docker.com/products/docker-desktop

#### Installing Docker Compose

Docker Compose is included with Docker Desktop. For Linux:
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## Installation Methods

### Method 1: Using the FIM Control Script (Recommended)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/BasicFIM.git
   cd BasicFIM
   ```

2. **Make the control script executable:**
   ```bash
   chmod +x fim
   ```

3. **Start the system:**
   ```bash
   # Development mode
   ./fim start
   
   # Production mode
   ./fim start --production
   ```

### Method 2: Using Scripts Directly

1. **Clone and navigate:**
   ```bash
   git clone https://github.com/your-username/BasicFIM.git
   cd BasicFIM
   ```

2. **Make scripts executable:**
   ```bash
   chmod +x scripts/*.sh
   ```

3. **Start the system:**
   ```bash
   # Development
   ./scripts/start-fim.sh
   
   # Production
   ./scripts/start-fim.sh --production
   ```

### Method 3: Using Makefile

1. **Clone and navigate:**
   ```bash
   git clone https://github.com/your-username/BasicFIM.git
   cd BasicFIM
   ```

2. **View available commands:**
   ```bash
   make help
   ```

3. **Start the system:**
   ```bash
   # Development
   make start
   
   # Production
   make start-prod
   ```

### Method 4: Manual Docker Commands

1. **Clone and navigate:**
   ```bash
   git clone https://github.com/your-username/BasicFIM.git
   cd BasicFIM
   ```

2. **Create required directories:**
   ```bash
   mkdir -p data logs
   ```

3. **Initialize database:**
   ```bash
   docker-compose -f docker/docker-compose.yml run --rm fim-db-init
   ```

4. **Start services:**
   ```bash
   docker-compose -f docker/docker-compose.yml up -d
   ```

## Post-Installation

### Verify Installation

1. **Check container status:**
   ```bash
   ./fim status
   ```

2. **Access web interface:**
   - Open http://localhost:3000 in your browser

3. **Check API:**
   - Visit http://localhost:8000/docs for API documentation

### Configuration

Edit `config/config.yaml` to customize:
- Monitoring paths
- Security profiles
- Scan intervals
- Excluded patterns

## Troubleshooting

### Common Issues

**Port conflicts:**
```bash
# Check what's using the ports
lsof -i :3000
lsof -i :8000
```

**Permission issues:**
```bash
# Fix Docker permissions (Linux)
sudo usermod -aG docker $USER
newgrp docker
```

**Container build failures:**
```bash
# Clear Docker cache and rebuild
docker system prune -a
./fim start --clean
```

### Getting Help

- Check logs: `./fim logs`
- View container status: `./fim status`
- Clean restart: `./fim clean && ./fim start`

## Uninstallation

```bash
# Stop all services
./fim stop

# Clean all data
./fim clean

# Remove project directory
cd ..
rm -rf BasicFIM
```
