# ⚡ HyperClaw - Standalone Local AI Assistant & Agent

`HyperClaw` is a local-first, privacy-centric AI assistant and autonomous agent framework. It is designed for complete independence from corporate control, leveraging the `Hyperion` inference engine for fast local execution while providing optional cloud fallbacks.

## 📁 Project Overview

- **Purpose:** A standalone AI assistant that runs on your hardware, with your rules. No internet required (after setup), no telemetry, and a "frozen" codebase to ensure stability and privacy.
- **Technologies:** 
  - **Inference:** `Hyperion` (a `llama.cpp` based engine) for local GGUF models.
  - **Logic:** Python 3.7+ (minimal dependencies, primarily standard library).
  - **Autonomy:** Built-in `TOOL_CALL` protocol for file I/O, directory listing, and shell command execution.
  - **Persistence:** `SessionManager` for conversation history and state.
- **Architecture:** 
  - **Modular Backends:** `LocalBackend` (direct binary), `SocketBackend` (model server), and Cloud Backends (Anthropic, Mistral, OpenAI).
  - **Tool Emulation:** A text-based loop that interprets model outputs as system tools for local models.
  - **Safety:** `safe_write_file` for guarded modifications with syntax checking and backups.

## 🚀 Building and Running

### Prerequisites
- **Hyperion Engine:** Must be built in `~/hyperion/build/` (see the global `GEMINI.md`).
- **Models:** GGUF model files should be placed in the `models/` directory.
- **Symlink:** Ensure `hyperion/` in the project root is a symlink to the `Hyperion` build directory:
  ```bash
  ln -s ~/hyperion/build hyperclaw/hyperion
  ```

### Key Commands
- **Run Assistant:**
  ```bash
  ./hyperclaw.py
  ```
- **Sync API Keys:** Sync keys from the primary OpenClaw configuration:
  ```bash
  ./sync_api_keys.py
  ```
- **Testing:** Run the script and use internal commands like `/help`, `/model`, or `/config` to verify the state.

## 🛠️ Development Conventions

- **Tool Protocol:** Models are instructed via `TOOL_EMULATION_PROMPT` to use:
  - `TOOL_CALL: {"name": "read_file", "args": {"path": "..."}}`
  - `TOOL_CALL: {"name": "write_file", "args": {"path": "...", "content": "..."}}`
  - `TOOL_CALL: {"name": "exec_command", "args": {"command": "..."}}`
  - `TOOL_CALL: {"name": "list_directory", "args": {"path": "..."}}`
- **Context Management:** Uses a sliding window (default 10 exchanges) and system prompts defined in `config.json`.
- **Error Handling:** `ErrorJournal` logs backend errors into `~/.hyperclaw/errors.jsonl` for pattern recognition and debugging.
- **Safety Protocol:**
  - Mandatory backups for modified `.py` files (e.g., `hyperclaw.py.bak`).
  - Python syntax validation before writing to any `.py` file.
- **Philosophy:** "Frozen" code—only update when manually requested to maintain stability and avoid upstream "bloat."

## 📄 Key Documentation
- `HYPERCLAW_README.md`: High-level quick start and philosophy.
- `HYPERCLAW_DESIGN.md`: Detailed architecture and liberation strategy.
- `HYPERCLAW_STATUS.md`: Current implementation progress and roadmap.

---
*Note: This GEMINI.md provides contextual mandates for AI-assisted development of HyperClaw.*
