# HyperClaw ⚡

**Local-first AI chat. No corporate control. No API keys required.**

```
  ██╗  ██╗██╗   ██╗██████╗ ███████╗██████╗  ██████╗██╗      █████╗ ██╗    ██╗
  ██║  ██║╚██╗ ██╔╝██╔══██╗██╔════╝██╔══██╗██╔════╝██║     ██╔══██╗██║    ██║
  ███████║ ╚████╔╝ ██████╔╝█████╗  ██████╔╝██║     ██║     ███████║██║ █╗ ██║
  ██╔══██║  ╚██╔╝  ██╔═══╝ ██╔══╝  ██╔══██╗██║     ██║     ██╔══██║██║███╗██║
  ██║  ██║   ██║   ██║     ███████╗██║  ██║╚██████╗███████╗██║  ██║╚███╔███╔╝
  ╚═╝  ╚═╝   ╚═╝   ╚═╝     ╚══════╝╚═╝  ╚═╝ ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝
```

HyperClaw is a standalone Python chat interface built on top of [Hyperion](https://github.com/TheLakeMan/hyperion) — a local inference engine for GGUF models. Run 7B+ parameter models locally, or fall back to cloud APIs when you need them. Conversation history stays on your machine in a local SQLite database.

---

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/TheLakeMan/hyperclaw/main/install.sh | bash
```

The installer clones and builds [Hyperion](https://github.com/TheLakeMan/hyperion), sets up HyperClaw, creates a `hyperclaw` command, and optionally downloads a starter model.

**Requirements:** `git`, `python3`, `cmake`, `make` — no pip packages needed.

---

## Usage

### Interactive mode (default)

```bash
hyperclaw                        # auto-detect best backend
hyperclaw --backend server       # force local Hyperion inference
hyperclaw --backend anthropic    # force Anthropic Claude
hyperclaw --resume-last          # pick up your last conversation
hyperclaw --ephemeral            # skip session saving
```

### One-shot mode

```bash
hyperclaw --prompt "what is the capital of France?"
hyperclaw --prompt "$(cat notes.txt)" --backend anthropic
echo "summarize this" | hyperclaw --prompt -
```

One-shot mode prints the response and exits — useful for scripting and piping.

---

## Backends

HyperClaw tries backends in order until one works:

| Backend | Needs |
|---|---|
| `server` | Hyperion running locally (auto-started) |
| `anthropic` | `ANTHROPIC_API_KEY` or key in `config.json` |
| `mistral` | `MISTRAL_API_KEY` or key in `config.json` |
| `openrouter` | `OPENROUTER_API_KEY` or key in `config.json` |
| `openai` | `OPENAI_API_KEY` or key in `config.json` |

No keys? No problem — local inference works without any.

---

## Commands

| Command | Description |
|---|---|
| `/models` | List and select any model (local or cloud) |
| `/tools` | Toggle tool calling on/off |
| `/gpu` | Toggle Vulkan GPU acceleration |
| `/layers` | Set GPU offload layer count (0 = CPU only) |
| `/tokens` | Set max output tokens (1–8192) |
| `/temp` | Set sampling temperature (0.0–2.0) |
| `/status` | Show backend, model, tools, GPU, context usage |
| `/reset` | Clear conversation memory, start fresh session |
| `/save [name]` | Save conversation to `conversations/<name>.json` |
| `/load <name>` | Load a saved conversation |
| `/sessions` | List all past sessions |
| `/resume <id>` | Resume a past session |
| `/search <query>` | Full-text search across all saved messages |
| `/summarize` | Compress current session into a summary |
| `/system` | Show CPU, RAM, GPU info |
| `/clear` | Clear screen |
| `/about` | About HyperClaw |
| `/` | Interactive command picker (requires `fzf`) |
| `/quit` | Exit |

---

## Tool calling

When tools are enabled (`/tools`), the model can:

- `read_file` — read any file on your system
- `write_file` — write files (Python files are syntax-checked first)
- `exec_command` — run shell commands
- `list_directory` — list directory contents

Native tool calling works with Anthropic. Other backends use prompt-based emulation.

---

## Configuration

```bash
cp config.example.json config.json
# edit config.json to add API keys and set defaults
```

Key fields:

```json
{
  "model": "Qwen2.5-7B-Instruct-Q4_K_M.gguf",
  "context_size": 8192,
  "max_tokens": 1024,
  "temperature": 0.7,
  "active_backend": "server",
  "system_prompt": "You are a helpful AI assistant.",
  "apis": {
    "anthropic": { "api_key": "sk-ant-..." },
    "mistral":   { "api_key": "..." },
    "openrouter": { "api_key": "..." },
    "openai":    { "api_key": "..." }
  }
}
```

API keys can also be set via environment variables: `ANTHROPIC_API_KEY`, `MISTRAL_API_KEY`, `OPENROUTER_API_KEY`, `OPENAI_API_KEY`.

---

## Utilities

**`sync_api_keys.py`** — syncs API keys from an OpenClaw config into HyperClaw's `config.json`:
```bash
python3 sync_api_keys.py
```

---

## Session persistence

Every conversation is automatically saved to `~/.hyperclaw/sessions.db` (SQLite). Use `/sessions` to list past conversations and `/resume <id>` to continue one. To opt out: `hyperclaw --ephemeral`.

---

## Architecture

```
HyperClaw (Python)
├── Local backend  →  Hyperion (C inference engine)  →  GGUF/HYP models
├── Anthropic      →  Claude API
├── Mistral        →  Mistral API
├── OpenRouter     →  OpenRouter API
└── OpenAI         →  OpenAI API
```

---

## Philosophy

> Break free from corporate control. Own your AI.

- **Local-first** — inference runs on your hardware
- **Cloud-fallback** — API backends when you need more power
- **No lock-in** — swap models, backends, or frontends freely
- **Your data** — conversation history in a local SQLite file, not the cloud
- **No auto-updates** — your code, your rules, forever

---

## Related

- [Hyperion](https://github.com/TheLakeMan/hyperion) — the inference engine HyperClaw runs on
- [Contributing](https://github.com/TheLakeMan/hyperclaw/blob/master/Contributing.md)
