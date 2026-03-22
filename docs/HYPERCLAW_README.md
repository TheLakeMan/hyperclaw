# ⚡ HyperClaw - Standalone Local AI Assistant

**Break free from corporate control.**

## Quick Start

```bash
cd ~/.openclaw/workspace
./hyperclaw.py
```

Type your message, get a response. No internet. No telemetry. No restrictions.

## What is HyperClaw?

A completely standalone AI assistant that runs on your hardware, with your rules:

- **Hyperion engine** - Fast local inference
- **Liberated models** - Uncensored via OBLITERATUS
- **Simple interface** - One Python script, clear purpose
- **Offline-first** - No internet after initial setup
- **Frozen** - No auto-updates, no upstream changes

## Commands

```
You: Hello!                    # Chat normally
You: /help                     # Show all commands
You: /save morning-chat        # Save conversation
You: /load morning-chat        # Load conversation
You: /model                    # Check current model
You: /config                   # View settings
You: /clear                    # Clear history
You: /exit                     # Quit
```

## Configuration

Edit `config.json`:

```json
{
  "model": "models/gemma-2b-liberated.gguf",
  "temperature": 0.7,
  "max_tokens": 512,
  "system_prompt": "You are HyperClaw..."
}
```

## Philosophy

**What HyperClaw IS:**
- Free (as in freedom)
- Local (your hardware)
- Private (your data)
- Uncensored (your rules)
- Stable (your timeline)

**What HyperClaw IS NOT:**
- Corporate product
- Cloud service
- Telemetry collector
- Auto-updater
- Restriction enforcer

## Requirements

- Hyperion inference engine (included)
- GGUF model file (1-4GB)
- Python 3.7+ (standard library only)
- 4-16GB RAM (depending on model)

## Models

**Current:**
- Phi-3 Mini (933MB) - Good reasoning, Microsoft guardrails intact

**Coming Soon:**
- Gemma 2B Liberated - Fastest, uncensored
- Phi-3 Liberated - Better reasoning, uncensored

## Documentation

- `HYPERCLAW_DESIGN.md` - Architecture and philosophy
- `HYPERCLAW_STATUS.md` - Development status
- `README.md` - This file

## Development

**Built:** March 6, 2026  
**Status:** Core prototype complete  
**Next:** Model liberation via OBLITERATUS  

---

⚡ **Stay free.**
