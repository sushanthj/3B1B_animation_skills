#!/usr/bin/env bash
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SETUP_DIR="$REPO_DIR/setup"

echo ""
echo "=== 3brown1blue setup ==="
echo ""

# ── GPU check ─────────────────────────────────────────────────────────────

COMPOSE_CMD="docker compose -f $SETUP_DIR/docker-compose.yml"

if nvidia-smi &>/dev/null 2>&1; then
    echo "NVIDIA GPU detected."

    HAS_TOOLKIT=false
    if dpkg -l nvidia-container-toolkit 2>/dev/null | grep -q "^ii" || \
       rpm -q nvidia-container-toolkit &>/dev/null 2>/dev/null; then
        HAS_TOOLKIT=true
    fi

    if [ "$HAS_TOOLKIT" = true ]; then
        echo "nvidia-container-toolkit is installed — enabling GPU passthrough."
        COMPOSE_CMD="docker compose -f $SETUP_DIR/docker-compose.yml -f $SETUP_DIR/docker-compose.gpu.yml"
    else
        echo ""
        echo "WARNING: nvidia-container-toolkit is not installed."
        echo "To enable GPU passthrough, install it first:"
        echo ""
        echo "  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg"
        echo "  curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \\"
        echo "    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \\"
        echo "    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list"
        echo "  sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit"
        echo "  sudo nvidia-ctk runtime configure --runtime=docker"
        echo "  sudo systemctl restart docker"
        echo ""
        echo "Proceeding without GPU access..."
    fi
else
    echo "No NVIDIA GPU detected — proceeding without GPU."
fi

# ── Build & enter container ───────────────────────────────────────────────

echo ""
echo "Building container..."
cd "$REPO_DIR"
$COMPOSE_CMD build

echo ""
echo "=== Setup complete ==="
echo ""
echo "Container is ready. Run animations from the host by asking your Cluade/Windsurf/Cursor/etc. to run commands like:"
echo "  'Create an animation of a blue circle morphing into a red square, and save it as blue_to_red.mp4'"
echo ""
echo "Or stop everything with: ./stop.sh"
echo ""
