#!/usr/bin/env bash
# HyperClaw installer
# Sets up Hyperion (inference engine) + HyperClaw (chat interface)
# Usage: curl -fsSL https://raw.githubusercontent.com/TheLakeMan/hyperclaw/main/install.sh | bash

set -e

HYPERION_REPO="https://github.com/TheLakeMan/hyperion.git"
HYPERCLAW_REPO="https://github.com/TheLakeMan/hyperclaw.git"
INSTALL_DIR="$HOME/hyperclaw"
HYPERION_DIR="$HOME/hyperion"
BIN_DIR="$HOME/.local/bin"

# ── Colors ────────────────────────────────────────────────────────────────────
CYAN='\033[38;5;51m'; YELLOW='\033[38;5;226m'; RED='\033[38;5;196m'; NC='\033[0m'
info()    { echo -e "${CYAN}  →${NC} $1"; }
warn()    { echo -e "${YELLOW}  ⚠${NC} $1"; }
success() { echo -e "${CYAN}  ✓${NC} $1"; }
die()     { echo -e "${RED}  ✗${NC} $1"; exit 1; }

echo -e "\n${CYAN}"
cat << 'EOF'
  ██╗  ██╗██╗   ██╗██████╗ ███████╗██████╗  ██████╗██╗      █████╗ ██╗    ██╗
  ██║  ██║╚██╗ ██╔╝██╔══██╗██╔════╝██╔══██╗██╔════╝██║     ██╔══██╗██║    ██║
  ███████║ ╚████╔╝ ██████╔╝█████╗  ██████╔╝██║     ██║     ███████║██║ █╗ ██║
  ██╔══██║  ╚██╔╝  ██╔═══╝ ██╔══╝  ██╔══██╗██║     ██║     ██╔══██║██║███╗██║
  ██║  ██║   ██║   ██║     ███████╗██║  ██║╚██████╗███████╗██║  ██║╚███╔███╔╝
  ╚═╝  ╚═╝   ╚═╝   ╚═╝     ╚══════╝╚═╝  ╚═╝ ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝
EOF
echo -e "${NC}"
echo "  Local-first AI. No corporate control. No API keys required."
echo ""

# ── Check dependencies ────────────────────────────────────────────────────────
info "Checking dependencies..."
command -v git  >/dev/null 2>&1 || die "git is required (apt install git / pacman -S git)"
command -v python3 >/dev/null 2>&1 || die "python3 is required"
command -v cmake >/dev/null 2>&1 || warn "cmake not found — Hyperion (local inference) won't build. Cloud backends will still work."
command -v make  >/dev/null 2>&1 || warn "make not found — same as above."

HAS_BUILD=true
command -v cmake >/dev/null 2>&1 && command -v make >/dev/null 2>&1 || HAS_BUILD=false

# ── Install Hyperion (inference engine) ───────────────────────────────────────
if [ "$HAS_BUILD" = true ]; then
    info "Installing Hyperion inference engine..."
    if [ -d "$HYPERION_DIR" ]; then
        info "Hyperion already exists at $HYPERION_DIR — pulling latest..."
        cd "$HYPERION_DIR" && git pull --quiet
    else
        git clone --quiet "$HYPERION_REPO" "$HYPERION_DIR"
    fi

    info "Building Hyperion (this takes a few minutes)..."
    cd "$HYPERION_DIR"

    # Detect Vulkan support
    VULKAN_FLAG=""
    if command -v vulkaninfo >/dev/null 2>&1 || [ -d /usr/include/vulkan ]; then
        info "Vulkan detected — enabling GPU acceleration"
        VULKAN_FLAG="-DLLAMA_VULKAN=ON"
    else
        warn "Vulkan not found — building CPU-only (still fast!)"
    fi

    mkdir -p build && cd build
    cmake .. -DCMAKE_BUILD_TYPE=Release $VULKAN_FLAG -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DBUILD_SHARED_LIBS=OFF -DLLAMA_CURL=OFF -DLLAMA_BUILD_SERVER=OFF 2>&1 | tail -3
    make -j"$(nproc)" hyperion hyperion_generate model_server_socket 2>&1 | tail -5

    success "Hyperion built at $HYPERION_DIR/build/"
else
    warn "Skipping Hyperion build — cloud backends (Anthropic, Mistral, OpenRouter) will work without it."
fi

# ── Install HyperClaw ─────────────────────────────────────────────────────────
info "Installing HyperClaw..."
if [ -d "$INSTALL_DIR" ]; then
    info "HyperClaw already exists at $INSTALL_DIR — pulling latest..."
    cd "$INSTALL_DIR" && git pull --quiet
else
    git clone --quiet "$HYPERCLAW_REPO" "$INSTALL_DIR"
fi

# Link Hyperion build into HyperClaw dir for auto-discovery
if [ "$HAS_BUILD" = true ] && [ -d "$HYPERION_DIR/build" ]; then
    ln -sf "$HYPERION_DIR/build" "$INSTALL_DIR/hyperion"
    success "Linked Hyperion build → $INSTALL_DIR/hyperion"
fi

# Copy example config if no config exists
if [ ! -f "$INSTALL_DIR/config.json" ]; then
    cp "$INSTALL_DIR/config.example.json" "$INSTALL_DIR/config.json"
    success "Created config.json from template"
    warn "Edit $INSTALL_DIR/config.json to add API keys (optional — only needed for cloud backends)"
fi

# ── Create hyperclaw command ───────────────────────────────────────────────────
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/hyperclaw" << SCRIPT
#!/usr/bin/env bash
exec python3 "$INSTALL_DIR/hyperclaw.py" "\$@"
SCRIPT
chmod +x "$BIN_DIR/hyperclaw"
success "Created command: $BIN_DIR/hyperclaw"

# ── Check PATH ────────────────────────────────────────────────────────────────
if ! echo "$PATH" | grep -q "$BIN_DIR"; then
    warn "$BIN_DIR is not in your PATH. Add this to your ~/.bashrc or ~/.zshrc:"
    echo ""
    echo '    export PATH="$HOME/.local/bin:$PATH"'
    echo ""
fi

# ── Download a starter model (optional) ───────────────────────────────────────
if [ "$HAS_BUILD" = true ]; then
    echo ""
    echo "  Download a starter model? (Qwen2.5-7B, ~4GB — best quality/speed balance)"
    read -r -p "  [y/N]: " DOWNLOAD_MODEL
    if [[ "$DOWNLOAD_MODEL" =~ ^[Yy]$ ]]; then
        MODEL_DIR="$HYPERION_DIR/models"
        mkdir -p "$MODEL_DIR"
        MODEL_URL="https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf"
        MODEL_FILE="$MODEL_DIR/Qwen2.5-7B-Instruct-Q4_K_M.gguf"
        info "Downloading Qwen2.5-7B (4GB)..."
        if command -v curl >/dev/null 2>&1; then
            curl -L --progress-bar -o "$MODEL_FILE" "$MODEL_URL"
        else
            wget -q --show-progress -O "$MODEL_FILE" "$MODEL_URL"
        fi
        success "Model saved to $MODEL_FILE"
    fi
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "  ${CYAN}⚡ HyperClaw installed!${NC}"
echo ""
echo "  Start chatting:"
echo "    hyperclaw                    # auto-detect best backend"
echo "    hyperclaw --backend server   # force local inference"
echo "    hyperclaw --ephemeral        # no session saving"
echo "    hyperclaw --resume-last      # pick up where you left off"
echo ""
echo "  Commands inside HyperClaw:"
echo "    /models    select model or cloud backend"
echo "    /tools     toggle tool calling"
echo "    /gpu       toggle Vulkan GPU acceleration"
echo "    /status    show current config"
echo "    /          fzf command picker (if fzf installed)"
echo ""
