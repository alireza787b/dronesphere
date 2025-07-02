#!/usr/bin/env bash

# =============================================================================
# 🚀 setup_ollama.sh
# Professional, robust installer for Ollama LLM on Ubuntu with NVIDIA GPU or Docker
# Supports optional NetBird, SSH-proxy, Docker container mode, or direct installation
# =============================================================================

set -euo pipefail
IFS=$'\n\t'

### ==================== CONFIGURATION ==================== ###
# Modes: set any to true as needed
ENABLE_NETBIRD=false          # Install/configure NetBird mesh
ENABLE_SSH_PROXY=false        # Route script traffic via SSH tunnel
ENABLE_DOCKER_MODE=false      # Run Ollama in Docker container

# SSH proxy defaults (if ENABLE_SSH_PROXY=true)
PROXY_USER=""
PROXY_HOST=""
PROXY_PORT=22
LOCAL_SOCKS_PORT=1080

# Ollama API (if not using Docker) or published port (if Docker)
OLLAMA_HOST="0.0.0.0"
OLLAMA_PORT=11434

# Preferred models to pull or pre-load (editable list)
MODELS=(
  "llama2:latest"
  "mistral:latest"
  "deepseek:latest"
)

### ==================== LOGGING ==================== ###
log()  { echo -e "[\e[1;34mINFO\e[0m] $*"; }
error(){ echo -e "[\e[1;31mERROR\e[0m] $*" >&2; exit 1; }

### ==================== PRIVILEGE CHECK ==================== ###
[[ $(id -u) -ne 0 ]] && error "Run as root or via sudo."

### ==================== SSH PROXY SETUP ==================== ###
if [[ "$ENABLE_SSH_PROXY" == true ]]; then
  log "SSH proxy enabled. Please provide connection details."
  read -p "Proxy SSH user: " PROXY_USER
  read -p "Proxy SSH host: " PROXY_HOST
  read -p "Proxy SSH port [22]: " input_port; PROXY_PORT=${input_port:-$PROXY_PORT}
  read -p "Local SOCKS port [1080]: " input_ls; LOCAL_SOCKS_PORT=${input_ls:-$LOCAL_SOCKS_PORT}

  log "Starting SSH dynamic tunnel on port ${LOCAL_SOCKS_PORT}..."
  ssh -o ExitOnForwardFailure=yes -f -N -D ${LOCAL_SOCKS_PORT} -p ${PROXY_PORT} ${PROXY_USER}@${PROXY_HOST}
  export ALL_PROXY="socks5h://127.0.0.1:${LOCAL_SOCKS_PORT}"
  export HTTP_PROXY="${ALL_PROXY}" HTTPS_PROXY="${ALL_PROXY}"
else
  log "Skipping SSH proxy configuration."
fi

### ==================== Docker Mode ==================== ###
if [[ "$ENABLE_DOCKER_MODE" == true ]]; then
  log "Docker mode enabled. Installing Docker and running Ollama container..."

  # Install Docker if missing
  if ! command -v docker &> /dev/null; then
    log "Installing Docker Engine..."
    apt-get update -y
    apt-get install -y \
      ca-certificates curl gnupg lsb-release
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
      | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
      https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
      | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  else
    log "Docker already installed."
  fi

  # Optionally install NVIDIA Container Toolkit if GPU acceleration desired
  if lspci | grep -i nvidia &> /dev/null; then
    log "NVIDIA GPU found. Installing NVIDIA Container Toolkit..."
    distribution="$(."/etc/os-release";echo $ID$VERSION_ID)"
    curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | apt-key add -
    curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list \
      | tee /etc/apt/sources.list.d/nvidia-docker.list
    apt-get update -y
    apt-get install -y nvidia-docker2
    systemctl restart docker
  fi

  # Pull & run Ollama container
  log "Pulling Ollama Docker image..."
  docker pull ollama/ollama
  log "Running Ollama container..."
  docker rm -f ollama &> /dev/null || true
  if lspci | grep -i nvidia &> /dev/null; then
    docker run -d --gpus=all \
      -v ollama:/root/.ollama \
      -p ${OLLAMA_PORT}:11434 \
      --name ollama ollama/ollama
  else
    docker run -d \
      -v ollama:/root/.ollama \
      -p ${OLLAMA_PORT}:11434 \
      --name ollama ollama/ollama
  fi

  log "Ollama container is running on port ${OLLAMA_PORT}."
  log "Skipping local install steps."
  goto END
else
  log "Docker mode disabled; proceeding with local installation."
fi

### ==================== INSTALL PREREQUISITES ==================== ###
log "Updating package list and installing dependencies..."
apt-get update -y
apt-get install -y \
  build-essential curl ca-certificates apt-transport-https gnupg \
  software-properties-common ufw lsb-release

### ==================== NVIDIA DRIVER ==================== ###
log "Detecting NVIDIA GPU..."
if lspci | grep -i nvidia &> /dev/null; then
  log "Installing recommended NVIDIA drivers..."
  ubuntu-drivers autoinstall
  log "⚠️  A reboot may be required."
else
  log "No NVIDIA GPU detected."
fi

### ==================== NetBird (Optional) ==================== ###
if [[ "$ENABLE_NETBIRD" == true ]]; then
  log "Configuring NetBird..."
  if ! command -v netbird &> /dev/null; then
    curl -fsSL https://apt.netbird.io/netbird.gpg \
      | tee /usr/share/keyrings/netbird-archive-keyring.gpg
    echo "deb [signed-by=/usr/share/keyrings/netbird-archive-keyring.gpg] \
      https://apt.netbird.io/ubuntu $(lsb_release -cs) main" \
      | tee /etc/apt/sources.list.d/netbird.list
    apt-get update -y && apt-get install -y netbird
  fi
  systemctl enable --now netbird
else
  log "Skipping NetBird."
fi

### ==================== FIREWALL ==================== ###
log "Allowing SSH and Ollama port through UFW..."
ufw allow OpenSSH
ufw allow ${OLLAMA_PORT}/tcp
ufw --force enable

### ==================== Ollama Installation ==================== ###
log "Checking Ollama binary..."
if ! command -v ollama &> /dev/null; then
  log "Installing Ollama..."
  curl -fsSL https://ollama.com/install.sh | sh
else
  log "Ollama already present."
fi

### ==================== Ollama Service ==================== ###
log "Setting up Ollama systemd service..."
cat > /etc/systemd/system/ollama.service <<EOF
[Unit]
Description=Ollama LLM Server
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/ollama serve --host ${OLLAMA_HOST} --port ${OLLAMA_PORT}
Restart=on-failure
User=root

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now ollama

### ==================== Pull & Test Models ==================== ###
log "Pulling and testing models..."
for m in "${MODELS[@]}"; do
  log "Pull $m"; ollama pull "$m" || log "Failed $m"
  log "Test $m"; \
    if ollama run "$m" --quiet --prompt "Hello" &> /dev/null; then \
      log "✅ $m"; \
    else \
      log "❌ $m (check logs)"; \
    fi
done

END:
log "✔️  Setup complete. Ollama API: http://${OLLAMA_HOST}:${OLLAMA_PORT}"

# =============================================================================
#                       USAGE & TROUBLESHOOTING
# =============================================================================
# After a successful run, choose commands based on your mode:

if [[ "$ENABLE_DOCKER_MODE" == true ]]; then
  echo "\nDocker Mode Usage:";
  echo "  • List models in container: docker exec -it ollama ollama list";
  echo "  • Pull additional model:      docker exec -it ollama ollama pull <model>";
  echo "  • Run a completion:           docker exec -it ollama ollama run <model> --prompt 'Your prompt'";
  echo "  • CURL via host:              curl -X POST http://localhost:${OLLAMA_PORT}/v1/chat/completions -H 'Content-Type: application/json' -d '{\"model\":\"<model>\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello\"}]}'";
else
  echo "\nLocal Mode Usage:";
  echo "  • List models:               ollama list";
  echo "  • Pull model:                ollama pull <model>";
  echo "  • Run a completion:          ollama run <model> --prompt 'Your prompt'";
  echo "  • CURL via host:             curl -X POST http://${OLLAMA_HOST}:${OLLAMA_PORT}/v1/chat/completions -H 'Content-Type: application/json' -d '{\"model\":\"<model>\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello\"}]}'";
fi

# Troubleshooting:
#  • Check Ollama service:    systemctl status ollama
#  • View logs:               journalctl -u ollama.service
#  • Verify GPU driver:       nvidia-smi
#  • Docker logs (if used):   docker logs ollama
# =============================================================================
