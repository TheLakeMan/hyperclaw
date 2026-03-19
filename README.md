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

HyperClaw is a standalone Python chat interface built on top of [Hyperion](https://github.com/TheLakeMan/hyperion) — a local inference engine for GGUF models. Run 7B+ parameter models locally, or fall back to cloud APIs when you need them. Your conversation history stays on your machine, in a local SQLite database.

---

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/TheLakeMan/hyperclaw/main/install.sh | bash
```

The installer:
- Clones and builds [Hyperion](https://github.com/TheLakeMan/hyperion) (the inference engine)
- Sets up HyperClaw and creates a `hyperclaw` command
- Optionally downloads a starter model (Qwen2.5-7B, ~4GB)

**Dependencies:** `git`, `python3`, `cmake`, `make` — that's it. No pip packages required.

---

## Quick start

```bash
hyperclaw                    # auto-detect best backend
hyperclaw --backend server   # force local inference
hyperclaw --ephemeral        # skip session saving
hyperclaw --resume-last      # pick up your last conversation
```

---

## Backends

HyperClaw tries backends in order until one works:

| Backend | What it needs |
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
| `/layers` | Set GPU offload layer count |
| `/tokens` | Set max output tokens |
| `/temp` | Set sampling temperature |
| `/status` | Show current backend, model, context usage |
| `/reset` | Clear conversation memory |
| `/save [name]` | Save conversation to `conversations/<name>.json` |
| `/load <name>` | Load a saved conversation |
| `/sessions` | List all past sessions (SQLite) |
| `/resume <id>` | Resume a past session |
| `/search <query>` | Full-text search across all saved messages |
| `/summarize` | Compress current session into a summary |
| `/system` | Show CPU, RAM, GPU info |
| `/clear` | Clear screen |
| `/` | Interactive command picker (requires `fzf`) |
| `/quit` | Exit |

---

## Tool calling

When tools are enabled (`/tools`), HyperClaw gives the model access to:

- `read_file` — read any file on your system
- `write_file` — write files (Python files are syntax-checked before writing)
- `exec_command` — run shell commands
- `list_directory` — list directory contents

Tool calling works natively with Anthropic. Other backends use prompt-based emulation.

---

## Configuration

Copy the example config and add your API keys:

```bash
cp config.example.json config.json
```

Key fields:

```json
{
  "model": "Qwen2.5-7B-Instruct-Q4_K_M.gguf",
  "context_size": 8192,
  "max_tokens": 1024,
  "temperature": 0.7,
  "active_backend": "server",
  "apis": {
    "anthropic": { "api_key": "sk-ant-..." },
    "mistral":   { "api_key": "..." }
  }
}
```

---

## Session persistence

Every conversation is automatically saved to `~/.hyperclaw/sessions.db` (SQLite). Use `/sessions` to list past conversations and `/resume <id>` to pick one up.

To opt out: `hyperclaw --ephemeral`

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

Hyperion and HyperClaw are separate repos so Hyperion can be used independently (MCP integration, other frontends, scripting).

---

## Philosophy

> Break free from corporate control. Own your AI.

- **Local-first** — inference runs on your hardware, not a server farm
- **Cloud-fallback** — API backends available when you need more power
- **No lock-in** — swap models, backends, or frontends freely
- **Your data** — conversation history in a local SQLite file, not the cloud
- **No auto-updates** — your code, your rules, forever

---

## Related

- [Hyperion](https://github.com/TheLakeMan/hyperion) — the inference engine HyperClaw runs on
