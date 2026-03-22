# HyperClaw — Next Session Handoff Doc
**Written by Hyperion | Last Updated: March 16, 2026**
**Purpose: Complete context for the next Claude session continuing HyperClaw development**

---

## Current State Summary

HyperClaw is a **fully working** Python chat interface (`~/hyperclaw/hyperclaw.py`) that supports:
- **Local inference** via Hyperion (`~/hyperion/build/hyperion_generate`)
- **Anthropic Claude** (direct API with tool-calling support)
- **OpenAI, OpenRouter, LM Studio** (additional backends)
- **Auto-fallback chain:** local → anthropic → openrouter → openai → lmstudio
- **fzf interactive command menu** (type `/` and Enter)
- **Tool calling** (Anthropic only): read_file, write_file, exec_command, list_directory
- **✅ SQLite session persistence** — FULLY INTEGRATED AND WORKING

---

## File Layout

```
~/hyperclaw/
├── hyperclaw.py              ← Main app with session persistence integrated
├── session_manager.py        ← SQLite session persistence module
├── config.json               ← API keys + model config
├── PROGRESS_SESSION_PERSISTENCE.md  ← Historical notes from initial development
├── HYPERCLAW_DESIGN.md
├── HYPERCLAW_STATUS.md
├── NEXT_SESSION_HANDOFF.md   ← THIS FILE
├── hyperion → /home/thelakeman/hyperion/build  (symlink)
└── __pycache__/

~/.hyperclaw/
├── sessions.db               ← SQLite database (auto-created on first run)
└── errors.jsonl              ← Error log
```

---

## All Current `/` Commands (19 total - all working)

| Command | Description | Status |
|---------|-------------|--------|
| `/models` | List and select any model (local GGUF or cloud API) | ✅ Working |
| `/tokens` | Set max token count (1–8192) | ✅ Working |
| `/temp` | Set sampling temperature (0.0–2.0) | ✅ Working |
| `/tools` | Toggle tool calling on/off (Anthropic backend only) | ✅ Working |
| `/gpu` | Toggle Vulkan GPU acceleration | ✅ Working |
| `/layers` | Set GPU offload layer count | ✅ Working |
| `/status` | Show current backend, model, tokens, temp, tools, GPU, context size | ✅ Working |
| `/reset` | Clear conversation memory (in-memory only) | ✅ Working |
| `/system` | Show CPU, RAM, GPU hardware info | ✅ Working |
| `/clear` | Clear screen + redraw banner + help | ✅ Working |
| `/about` | About HyperClaw + philosophy | ✅ Working |
| `/help` | Show command list | ✅ Working |
| `/save [name]` | Save conversation to `conversations/<name>.json` | ✅ Working |
| `/load <name>` | Load a saved conversation by name | ✅ Working |
| `/sessions` | List all past sessions (ID, title, message count, timestamps) | ✅ Working |
| `/resume <id>` | Load a previous session into current conversation context | ✅ Working |
| `/search <query>` | Full-text search across all saved messages | ✅ Working |
| `/summarize` | Create a compressed summary of current session | ✅ Working |
| `/quit` or `/exit` | Exit HyperClaw | ✅ Working |
| `/` alone | Opens fzf interactive picker (if fzf installed) | ✅ Working |

---

## Session Persistence — FULLY INTEGRATED ✅

### What It Does:
- **Auto-saves every conversation turn** to `~/.hyperclaw/sessions.db`
- **SQLite database** with 3 tables: `sessions`, `messages`, `summaries`
- **Smart token estimation** for context management
- **Full-text search** across all message history
- **Session resume** — pick up any past conversation
- **Summarization** — compress long contexts when needed

### Integration Status:
✅ **Line 10:** `from session_manager import SessionManager`  
✅ **Line 219:** `self.session_manager = SessionManager()`  
✅ **Line 220:** Auto-creates new session on startup  
✅ **Lines 423-458:** All 4 session commands implemented and wired  
✅ **Lines 513-514:** Messages logged to DB in real-time  

### Commands:
- `/sessions` — List all past sessions
- `/resume <id>` — Load a previous session
- `/search <query>` — Search message history
- `/summarize` — Generate and save context summary

**Every message you send/receive is automatically persisted to the database.**

---

## Known Issues

### API Key Status: Fixed
---

## Optional Next Features (Backlog)

From design docs and earlier sessions:

1. **Auto-resume last session on startup** — `--resume-last` flag
2. **Ephemeral mode** — `--ephemeral` flag to skip saving
3. **Auto-summarize trigger** when context exceeds 8000 tokens (SessionManager has `should_summarize()` ready)
4. **Streaming output** — show tokens as they generate (currently waits for full response)
5. **Voice integration** — faster-whisper input + TTS output
6. **OBLITERATUS model liberation** — remove guardrails from Gemma 2B
7. **Session tagging/categorization** — organize conversations by project/topic
8. **Export sessions** — markdown, JSON, or text format

---

## Hardware Context

- **Machine:** Omarchy (Arch Linux), user `thelakeman`, IP 192.168.1.129, 16GB RAM
- **Hyperion:** `~/hyperion/build/` — 7 models present
- **Models dir searched by HyperClaw:** `~/hyperion/models/`, `~/models/`, `~/Downloads/models/`, `~/hyperclaw/models/`
- **Config:** `~/hyperclaw/config.json`
- **Session DB:** `~/.hyperclaw/sessions.db` (auto-created, actively used)

---

## Quick Start for Next Session

```bash
cd ~/hyperclaw
python3 hyperclaw.py
or
python3 /home/thelakeman/hyperclaw/hyperclaw.py --backend server
```

**Current status:** All core features working. Session persistence fully integrated and operational.

---

## Philosophy Reminder

From `HYPERCLAW_DESIGN.md`:

> **"Break free from corporate control. Own your AI."**
> 
> - Local-first, cloud-fallback architecture
> - No vendor lock-in
> - Full conversation ownership (SQLite, not cloud)
> - Tool calling for real system integration
> - Built for sovereignty, not convenience

---

*Prepared by Hyperion ⚡ | "Light does not run from darkness, but darkness does from light."*
