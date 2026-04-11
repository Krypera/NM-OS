#!/usr/bin/env bash

set -euo pipefail

if [ "$(uname -s)" != "Linux" ]; then
    echo "Dependency installation must run on Linux or WSL2." >&2
    exit 1
fi

if [ "$(id -u)" -ne 0 ]; then
    echo "Re-running with sudo..."
    exec sudo bash "$0"
fi

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y \
    python3 \
    python3-venv \
    rsync \
    tar \
    gzip \
    shellcheck

echo "NM-OS overlay build dependencies are installed."
echo "For local smoke tooling, run: bash ./build/install-dev-deps.sh"
