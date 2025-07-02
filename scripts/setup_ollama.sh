#!/usr/bin/env bash

# =============================================================================
# 🚀 setup_ollama.sh
# Professional, robust installer for Ollama LLM on Ubuntu with NVIDIA GPU
# Supports optional NetBird mesh or direct Internet exposure
# =============================================================================

set -euo pipefail
IFS=$'\n\t'

### ==================== CONFIGURATION ==================== ###
# Enable NetBird: set to true to install/configure NetBird, false to skip
ENABLE_NETBIRD=false
NETBIRD_INTERFACE="netbird0"

# Ollama API host and port (0.0.0.0 for all interfaces)
OLLAMA_HOST="0.0.0.0"
OLLAMA_PORT=11434

# Preferred models to pull (editable list)
MODELS=(
  "llama2:latest"
  "mistral:latest"
  "deepseek:latest"
)

### ==================== LOGGING ==================== ###
log() {
  echo -e "[\e[1;34mINFO\e[0m] $*"
}
error() {
  echo -e "[\e[1;31mERROR\e[0m] $*" >&2
  exit 1
}

### ==================== PRIVILEGE CHECK ==================== ###
if [[ $(id -u) -ne 0 ]]; then
  error "This script must be run as root or via sudo."
fi

### ==================== INSTALL PREREQUISITES ==================== ###
log "Updating package list and installing dependencies..."
apt-get update -y
apt-get install -y build-essential curl ca-certificates apt-transport-https gnupg software-properties-common ufw lsb-release

### ==================== NVIDIA DRIVER ==================== ###
log "Detecting NVIDIA GPU..."
if lspci | grep -i nvidia &> /dev/null; then
  log "NVIDIA GPU found. Installing recommended drivers..."
  ubuntu-drivers autoinstall
  log "⚠️  A reboot may be required to load new drivers."
else
  log "No NVIDIA GPU detected; skipping NVIDIA driver installation."
fi

### ==================== NetBird (Optional) ==================== ###
if [[ "$ENABLE_NETBIRD" == true ]]; then
  log "Configuring NetBird..."
  if ! command -v netbird &> /dev/null; then
    log "Installing NetBird client..."
    curl -fsSL https://apt.netbird.io/netbird.gpg | tee /usr/share/keyrings/netbird-archive-keyring.gpg >/dev/null
    echo "deb [signed-by=/usr/share/keyrings/netbird-archive-keyring.gpg] https://apt.netbird.io/ubuntu $(lsb_release -cs) main" \
      | tee /etc/apt/sources.list.d/netbird.list
    apt-get update -y
    apt-get install -y netbird
  else
    log "NetBird client already installed."
  fi
  log "Enabling and starting NetBird service..."
  systemctl enable --now netbird
else
  log "Skipping NetBird configuration (ENABLE_NETBIRD=false)."
fi

### ==================== FIREWALL ==================== ###
log "Configuring UFW to allow SSH and Ollama port..."
ufw allow OpenSSH
ufw allow ${OLLAMA_PORT}/tcp
ufw --force enable

### ==================== Ollama Installation ==================== ###
log "Checking Ollama..."
if ! command -v ollama &> /dev/null; then
  log "Installing Ollama..."
  curl -fsSL https://ollama.com/install.sh | sh
else
  log "Ollama already installed."
fi

### ==================== Ollama Service ==================== ###
log "Creating systemd unit for Ollama service..."
SERVICE_FILE="/etc/systemd/system/ollama.service"
cat > "$SERVICE_FILE" <<EOF
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

log "Reloading systemd and enabling Ollama service..."
systemctl daemon-reload
systemctl enable --now ollama

### ==================== Pull Models ==================== ###
log "Pulling preferred models..."
for model in "${MODELS[@]}"; do
  log "  ↳ Pulling $model..."
  if ! ollama pull "$model"; then
    log "    ⚠️  Failed to pull $model. Skipping..."
  fi
done

### ==================== Test Models ==================== ###
log "Testing models one by one..."
for model in "${MODELS[@]}"; do
  log "  ↳ Testing $model..."
  if ollama run "$model" --quiet --prompt "Hello" >/dev/null 2>&1; then
    log "    ✅ $model is responding"
  else
    log "    ❌ $model test failed"
    log "    Check logs: journalctl -u ollama.service"
  fi
done

### ==================== FINAL REPORT & USAGE GUIDE ==================== ###
log "✔️  Setup complete!"
log "Ollama API endpoint: http://${OLLAMA_HOST}:${OLLAMA_PORT}"

cat <<EOF

How to use from any machine (internet or NetBird):
  • CLI:
      ollama list
      ollama run <model> --prompt "Your prompt here"

  • HTTP API (curl example):
      curl -X POST http://${OLLAMA_HOST}:${OLLAMA_PORT}/v1/chat/completions \
        -H 'Content-Type: application/json' \
        -d '{"model":"${MODELS[0]}","messages":[{"role":"user","content":"Hello"}]}'

If you see errors:
  • Ensure Ollama service is running:  systemctl status ollama
  • Review logs:                 journalctl -u ollama.service
  • Verify GPU drivers:          nvidia-smi

EOF
