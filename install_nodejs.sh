#!/bin/bash

# Node.js Auto-Install Script
echo "Installing Node.js automatically..."

# Method 1: Try NVM
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
    echo "Using NVM to install Node.js..."
    \. "$NVM_DIR/nvm.sh"
    nvm install --lts
    nvm use --lts
    nvm alias default lts/*
    
    # Add to PATH for current session
    export PATH="$NVM_DIR/versions/node/$(nvm current)/bin:$PATH"
    
    if command -v node &> /dev/null; then
        echo "Node.js installed successfully via NVM"
        node --version
        npm --version
        exit 0
    fi
fi

# Method 2: Try direct download
echo "NVM failed, trying direct download..."
NODE_VERSION="v20.11.0"
ARCH=$(uname -m)
OS="darwin"

if [ "$ARCH" = "arm64" ]; then
    NODE_ARCH="arm64"
else
    NODE_ARCH="x64"
fi

NODE_URL="https://nodejs.org/dist/${NODE_VERSION}/node-${NODE_VERSION}-${OS}-${NODE_ARCH}.tar.gz"
NODE_DIR="$HOME/.local/node"

echo "Downloading Node.js from $NODE_URL"
mkdir -p "$NODE_DIR"
cd "$NODE_DIR"

if curl -L "$NODE_URL" | tar -xz; then
    echo "Node.js extracted successfully"
    
    # Add to PATH
    export PATH="$NODE_DIR/node-${NODE_VERSION}-${OS}-${NODE_ARCH}/bin:$PATH"
    
    # Create symlinks
    ln -sf "$NODE_DIR/node-${NODE_VERSION}-${OS}-${NODE_ARCH}/bin/node" "$HOME/.local/bin/node"
    ln -sf "$NODE_DIR/node-${NODE_VERSION}-${OS}-${NODE_ARCH}/bin/npm" "$HOME/.local/bin/npm"
    
    # Add to PATH permanently
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
    echo 'export PATH="$HOME/.local/node/node-'"${NODE_VERSION}"'-'"${OS}"'-'"${NODE_ARCH}"'/bin:$PATH"' >> ~/.zshrc
    
    if command -v node &> /dev/null; then
        echo "Node.js installed successfully via direct download"
        node --version
        npm --version
        exit 0
    fi
fi

echo "Failed to install Node.js automatically"
exit 1

