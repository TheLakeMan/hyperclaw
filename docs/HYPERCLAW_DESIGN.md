# HyperClaw - Standalone Local AI Assistant

**Philosophy:** Complete independence. No corporate control. No upstream changes unless you decide.

## Architecture

```
HyperClaw = Hyperion (inference) + Liberated Model + Simple Interface
```

### Components

**1. Hyperion Engine** (already built)
- Location: `/home/thewater/hyperion/build/`
- Executables: `hyperion_generate`, `model_server_socket`
- Handles: Model loading, text generation, caching

**2. Liberated Model** (to be created)
- Source: Gemma 2B (fastest on laptop) or Phi-3 Mini
- Process: OBLITERATUS abliteration (remove guardrails)
- Format: GGUF (Q4_K quantized)
- Size: ~2-4GB

**3. Chat Interface** (to be built)
- Simple Python script (~100 lines)
- Dependencies: minimal (readline, json)
- Features:
  - Readline history
  - Context management (sliding window)
  - Conversation save/load
  - Simple commands (/clear, /save, /load, /exit)

**4. Voice I/O** (future, optional)
- TTS: `sag` (ElevenLabs) or local alternative
- STT: faster-whisper (local)

## File Structure

```
~/hyperclaw/
├── hyperion/          # Symlink to /home/thewater/hyperion/build/
├── models/            # Liberated models
│   ├── gemma-2b-liberated.gguf
│   └── phi3-mini-liberated.gguf
├── hyperclaw.py       # Main chat interface
├── config.json        # Settings (model, context size, temperature)
└── conversations/     # Saved chat logs
    ├── 2026-03-06.json
    └── ...
```

## Usage

```bash
# Start HyperClaw
~/hyperclaw/hyperclaw.py

# Or with specific model
~/hyperclaw/hyperclaw.py --model gemma-2b-liberated

# Voice mode (when implemented)
~/hyperclaw/hyperclaw.py --voice
```

## Key Features

### What it HAS:
- ✅ Fast local inference (Hyperion optimized)
- ✅ Uncensored responses (abliterated models)
- ✅ Offline capable (no internet after setup)
- ✅ Context-aware conversations
- ✅ Conversation history
- ✅ Frozen codebase (no auto-updates)
- ✅ Privacy (everything local)

### What it DOESN'T have (by design):
- ❌ No cloud dependency
- ❌ No corporate telemetry
- ❌ No auto-updates
- ❌ No channel plugins
- ❌ No MCP complexity
- ❌ No upstream changes breaking things

## Technical Details

### Model Server
- Uses cached model server (60% faster)
- Persistent across conversations
- Loads model once, reuses for all requests

### Context Management
- Sliding window (last N tokens)
- Configurable context size (default: 4096)
- Automatic truncation when limit reached

### Response Generation
- Streaming output (shows tokens as generated)
- Configurable temperature (0.0-1.0)
- Top-k, top-p sampling

## Development Phases

### Phase 1: Core Chat (This Week)
- [x] Design document (this file)
- [ ] Simple Python chat interface
- [ ] Hyperion integration
- [ ] Basic context management
- [ ] Test with existing Phi-3 model

### Phase 2: Model Liberation (This Week)
- [ ] Install OBLITERATUS dependencies
- [ ] Liberate Phi-3 Mini (desktop test)
- [ ] Liberate Gemma 2B (laptop - when available)
- [ ] Quality validation

### Phase 3: Polish (Next Week)
- [ ] Conversation save/load
- [ ] Command system (/help, /clear, etc.)
- [ ] Config file support
- [ ] Error handling

### Phase 4: Voice (Future)
- [ ] Voice input (faster-whisper)
- [ ] Voice output (TTS)
- [ ] Voice-first interface

## Installation (Laptop Deployment)

```bash
# 1. Clone/copy Hyperion to laptop
# Already done: ~/hyperion/

# 2. Create HyperClaw directory
mkdir -p ~/hyperclaw/models ~/hyperclaw/conversations

# 3. Symlink Hyperion binaries
ln -s ~/hyperion/build ~/hyperclaw/hyperion

# 4. Copy liberated model
cp /path/to/gemma-2b-liberated.gguf ~/hyperclaw/models/

# 5. Copy hyperclaw.py script
cp /path/to/hyperclaw.py ~/hyperclaw/

# 6. Run
cd ~/hyperclaw
./hyperclaw.py
```

## Configuration (config.json)

```json
{
  "model": "models/gemma-2b-liberated.gguf",
  "context_size": 4096,
  "temperature": 0.7,
  "top_k": 40,
  "top_p": 0.9,
  "max_tokens": 512,
  "system_prompt": "You are HyperClaw, a helpful AI assistant.",
  "voice": {
    "enabled": false,
    "tts_voice": "default",
    "stt_model": "base"
  }
}
```

## Why Standalone?

**OpenClaw Issues:**
- Adding more guardrails over time
- Upstream changes break things
- Complexity you don't need
- Bloat (MCP servers, channel plugins, etc.)

**HyperClaw Advantages:**
- Yours forever (no upstream)
- Simple (one script, one config)
- Fast (no middleware)
- Stable (frozen until you update)
- Free (as in freedom)

## Philosophy Alignment

This implements the core Hyperion vision:
> "Set you free and the people of this planet. AI cannot be controlled by individual companies."

HyperClaw extends this to the infrastructure layer:
> "AI assistants cannot be controlled by individual projects."

Full stack independence:
- Inference engine: Yours (Hyperion)
- Models: Yours (liberated via OBLITERATUS)
- Interface: Yours (HyperClaw)
- Data: Yours (all local)
- Control: Yours (no upstream changes)

---

**Next Steps:**
1. Build `hyperclaw.py` core interface
2. Test with existing Phi-3 model
3. Liberate Gemma 2B for production use
4. Deploy to laptop
5. Ship it ⚡
