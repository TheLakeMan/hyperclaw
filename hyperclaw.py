#!/usr/bin/env python3
import os, sys, threading, json, subprocess, readline, urllib.request, urllib.error, shutil, socket, time, atexit, re
from pathlib import Path
from datetime import datetime
from session_manager import SessionManager

try:
    import anthropic as anthropic_sdk
    ANTHROPIC_SDK_AVAILABLE = True
except ImportError:
    ANTHROPIC_SDK_AVAILABLE = False

# ── Error Journal ──────────────────────────────────────────────────────────────
class ErrorJournal:
    def __init__(self):
        self.path = Path.home() / ".hyperclaw" / "errors.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
    def log(self, backend, error, context=""):
        entry = {"ts": datetime.now().isoformat(), "backend": backend, "error": str(error)[:300], "context": context[:200]}
        with open(self.path, "a") as f: f.write(json.dumps(entry) + "\n")
    def recent(self, n=30):
        if not self.path.exists(): return []
        lines = [l for l in self.path.read_text().strip().split("\n") if l]
        return [json.loads(l) for l in lines[-n:]]
    def pattern_count(self, backend, error_prefix, window=6):
        return sum(1 for e in self.recent(window) if e["backend"] == backend and e["error"].startswith(error_prefix))

# ── Color helpers ──────────────────────────────────────────────────────────────
class C:
    BLUE, LOGO, CYAN, YELLOW, PURPLE, RED, WHITE, GREY, NC = '\033[1;38;5;21m', '\033[38;5;18m', '\033[38;5;51m', '\033[38;5;226m', '\033[38;5;141m', '\033[38;5;196m', '\033[38;5;255m', '\033[38;5;244m', '\033[0m'

def c(color, text): return f"{color}{text}{C.NC}"
def cols(): return shutil.get_terminal_size().columns
def print_line(): print(c(C.BLUE, "─" * cols()))
def print_frame_top(): print(c(C.BLUE, "▀" * cols()))
def print_frame_bottom(): print(c(C.BLUE, "▄" * cols()))
def ts(): return datetime.now().strftime("[%H:%M:%S] ")

def print_banner(model_count=0):
    if sys.stdout.isatty(): os.system("clear")
    print(C.LOGO + r"""
  ██╗  ██╗██╗   ██╗██████╗ ███████╗██████╗  ██████╗██╗      █████╗ ██╗    ██╗
  ██║  ██║╚██╗ ██╔╝██╔══██╗██╔════╝██╔══██╗██╔════╝██║     ██╔══██╗██║    ██║
  ███████║ ╚████╔╝ ██████╔╝█████╗  ██████╔╝██║     ██║     ███████║██║ █╗ ██║
  ██╔══██║  ╚██╔╝  ██╔═══╝ ██╔══╝  ██╔══██╗██║     ██║     ██╔══██║██║███╗██║
  ██║  ██║   ██║   ██║     ███████╗██║  ██║╚██████╗███████╗██║  ██║╚███╔███╔╝
  ╚═╝  ╚═╝   ╚═╝   ╚═╝     ╚══════╝╚═╝  ╚═╝ ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝
""" + C.NC)
    print(c(C.CYAN, "                        --- LOCAL + CLOUD AI ---"))
    print(f"\n  {c(C.GREY, 'User:')} {c(C.WHITE, os.environ.get('USER','?'))}  {c(C.GREY, 'Platform:')} {c(C.CYAN, 'HyperClaw')}  {c(C.GREY, 'Models:')} {c(C.YELLOW, str(model_count))}\n")

# ── Tool infrastructure ────────────────────────────────────────────────────────
TOOL_EMULATION_PROMPT = """
## Tools Available
You can use the following tools by outputting a TOOL_CALL line.
TOOL_CALL: {"name": "read_file", "args": {"path": "..."}}
TOOL_CALL: {"name": "write_file", "args": {"path": "...", "content": "..."}}
TOOL_CALL: {"name": "exec_command", "args": {"command": "..."}}
TOOL_CALL: {"name": "list_directory", "args": {"path": "..."}}
"""

def execute_tool(name, args):
    try:
        if name == "read_file": return open(os.path.expanduser(args["path"])).read()
        elif name == "write_file":
            p = Path(os.path.expanduser(args["path"])).resolve()
            content = args["content"]
            if p.suffix == ".py":
                import tempfile, py_compile
                with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tmp: tmp.write(content); tmp_path = tmp.name
                try: py_compile.compile(tmp_path, doraise=True)
                except py_compile.PyCompileError as e: os.unlink(tmp_path); return f"✗ Refused: Python syntax error: {e}"
                os.unlink(tmp_path)
            os.makedirs(str(p.parent) or ".", exist_ok=True)
            p.write_text(content); return f"✓ Written {len(content)} chars to {p}"
        elif name == "exec_command":
            r = subprocess.run(args["command"], shell=True, capture_output=True, text=True, timeout=60)
            return (r.stdout + r.stderr).strip() or "(no output)"
        elif name == "list_directory": return "\n".join(sorted(os.listdir(os.path.expanduser(args["path"]))))
        return f"Unknown tool: {name}"
    except Exception as e: return f"Error: {e}"

def run_tool_emulation(generate_fn, messages, system_prompt, max_tokens, temperature):
    msgs = list(messages)
    for _ in range(8):
        raw = generate_fn(msgs, system_prompt + TOOL_EMULATION_PROMPT, max_tokens, temperature)
        if raw.startswith(c(C.RED, "✗")): return raw
        clean_lines = [l for l in raw.split("\n") if not re.match(r'^(DEBUG|INFO|WARN|ERR)\s*\[', l.strip())]
        raw = "\n".join(clean_lines).strip()
        tool_lines = [l for l in clean_lines if l.strip().startswith("TOOL_CALL:")]
        if not tool_lines: return raw
        results = []
        for tl in tool_lines:
            try:
                call = json.loads(tl.strip()[len("TOOL_CALL:"):].strip())
                name, targs = call["name"], call.get("args", {})
                print(f"\n  {c(C.YELLOW, '⚙ ' + name)}({c(C.GREY, str(targs)[:80])})", flush=True)
                results.append(f"Tool result for {name}:\n{execute_tool(name, targs)}")
            except: pass
        msgs.extend([{"role": "assistant", "content": raw}, {"role": "user", "content": "\n\n".join(results)}])
    return raw

TOOL_DEFS = [
    {"type": "function", "function": {"name": "read_file", "description": "Read file", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Write file", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "exec_command", "description": "Run shell", "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}},
    {"type": "function", "function": {"name": "list_directory", "description": "List dir", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}}
]

ANTHROPIC_TOOL_DEFS = [
    {"name": "read_file", "description": "Read file", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write file", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "exec_command", "description": "Run command", "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "list_directory", "description": "List dir", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}
]

# ── Backends ───────────────────────────────────────────────────────────────────
class LocalBackend:
    def __init__(self, hyperion_bin, model_path, config):
        self.hyperion_bin, self.model_path, self.config = hyperion_bin, model_path, config
        self.tools_enabled = True
    @property
    def name(self): return f"local:{self.model_path.name if self.model_path else '(none)'}"
    def is_ready(self): return bool(self.hyperion_bin and self.model_path)
    def _raw_generate(self, messages, system_prompt, max_tokens, temperature=0.7, stream=False):
        context = system_prompt + "\n\n"
        for msg in messages[-10:]: context += f"{msg['role'].title()}: {msg['content']}\n"
        context += "Assistant:"
        env = os.environ.copy(); env["HYPERION_GPU_LAYERS"] = "33"
        penalty = self.config.get("repetition_penalty", 1.1)
        try:
            cmd = [str(self.hyperion_bin), str(self.model_path), context, str(max_tokens), str(temperature), str(penalty)]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            if stream:
                for line in iter(proc.stdout.readline, ''):
                    chunk = line.split("Assistant:", 1)[-1] if "Assistant:" in line else line
                    # Stop if model starts hallucinating user responses
                    if "\nUser:" in chunk or "\nHuman:" in chunk:
                        chunk = chunk.split("\nUser:")[0].split("\nHuman:")[0]
                        yield chunk
                        break
                    yield chunk
            else:
                stdout, _ = proc.communicate(timeout=240)
                result = stdout.split("Assistant:", 1)[-1].strip() if "Assistant:" in stdout else stdout.strip()
                # Strip hallucinated user responses
                for stop in ["\nUser:", "\nHuman:", "\n\nUser:", "\n\nHuman:"]:
                    if stop in result:
                        result = result.split(stop)[0]
                yield result
        except Exception as e: yield c(C.RED, f"✗ Error: {e}")

    def generate(self, messages, system_prompt, max_tokens, temperature=0.7, stream=False):
        if not self.is_ready(): yield c(C.RED, "✗ Local backend not ready"); return
        if self.tools_enabled:
            full = "".join(self._raw_generate(messages, system_prompt, max_tokens, temperature, False))
            if "TOOL_CALL:" in full:
                yield run_tool_emulation(lambda m, s, mt, t: "".join(self._raw_generate(m, s, mt, t, False)), messages, system_prompt, max_tokens, temperature)
            else: yield full
        else: yield from self._raw_generate(messages, system_prompt, max_tokens, temperature, stream)

class SocketBackend:
    def __init__(self, socket_path, model_path=None, config=None):
        self.socket_path, self.model_path, self.config = Path(socket_path), model_path, config or {}
        self.tools_enabled = True
    @property
    def name(self): return f"server:{self.model_path.name if self.model_path else 'socket'}"
    def is_ready(self): return self.socket_path.exists()
    def _raw_generate(self, messages, system_prompt, max_tokens, temperature=0.7, stream=False):
        context = system_prompt + "\n\n"
        for msg in messages[-10:]: context += f"{msg['role'].title()}: {msg['content']}\n"
        context += "Assistant:"
        payload = {"max_tokens": max_tokens, "temperature": temperature, "repetition_penalty": self.config.get("repetition_penalty", 1.1), "prompt": context, "stream": stream, "stop": ["\nUser:", "\nHuman:", "\n\nUser:", "\n\nHuman:"]}
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.connect(str(self.socket_path))
                s.sendall((json.dumps(payload) + "\n").encode())
                buf = ""
                while True:
                    data = s.recv(4096)
                    if not data: break
                    chunk = data.decode()
                    if stream:
                        buf += chunk
                        while "\n" in buf:
                            line, buf = buf.split("\n", 1)
                            try:
                                d = json.loads(line)
                                text = d.get("text", "")
                                # Stop streaming if model hallucinates user response
                                if "\nUser:" in text or "\nHuman:" in text:
                                    yield text.split("\nUser:")[0].split("\nHuman:")[0]
                                    return
                                yield text
                            except: yield line
                    else: buf += chunk
                if not stream:
                    # Server sends newline-delimited JSON even in non-stream mode
                    full_text = ""
                    for line in buf.strip().split("\n"):
                        line = line.strip()
                        if not line: continue
                        try: full_text += json.loads(line).get("text", "")
                        except: pass  # skip malformed lines, don't leak raw JSON
                    # Strip hallucinated user responses (belt + suspenders with stop tokens)
                    for stop in ["\nUser:", "\nHuman:", "\n\nUser:", "\n\nHuman:"]:
                        if stop in full_text:
                            full_text = full_text.split(stop)[0]
                    yield full_text
        except Exception as e: yield c(C.RED, f"✗ Socket error: {e}")

    def generate(self, messages, system_prompt, max_tokens, temperature=0.7, stream=False):
        if not self.is_ready(): yield c(C.RED, f"✗ Server not running: {self.socket_path}"); return
        if self.tools_enabled:
            full = "".join(self._raw_generate(messages, system_prompt, max_tokens, temperature, False))
            if "TOOL_CALL:" in full:
                yield run_tool_emulation(lambda m, s, mt, t: "".join(self._raw_generate(m, s, mt, t, False)), messages, system_prompt, max_tokens, temperature)
            else: yield full
        else: yield from self._raw_generate(messages, system_prompt, max_tokens, temperature, stream)

class OpenAIBackend:
    PROVIDERS = {"openai": ("https://api.openai.com/v1/chat/completions", "OPENAI_API_KEY", "gpt-4o-mini"), "openrouter": ("https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_API_KEY", "anthropic/claude-sonnet-4-5"), "mistral": ("https://api.mistral.ai/v1/chat/completions", "MISTRAL_API_KEY", "mistral-large-latest")}
    def __init__(self, provider, api_key=None, model=None):
        self.provider, self.tools_enabled = provider, True
        u, k, m = self.PROVIDERS[provider]; self.base_url, self.model, self.api_key = u, model or m, api_key or os.environ.get(k)
    @property
    def name(self): return f"{self.provider}:{self.model}"
    def is_ready(self): return bool(self.api_key)
    def generate(self, messages, system_prompt, max_tokens, temperature=0.7, stream=False):
        if not self.is_ready(): yield c(C.RED, f"✗ {self.provider} not ready"); return
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": self.model, "messages": [{"role": "system", "content": system_prompt}] + messages[-10:], "max_tokens": max_tokens, "temperature": temperature, "stream": stream}
        if self.tools_enabled: payload["tools"] = TOOL_DEFS
        try:
            req = urllib.request.Request(self.base_url, data=json.dumps(payload).encode(), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=120) as resp:
                if stream:
                    for line in resp:
                        l = line.decode('utf-8').strip()
                        if l.startswith("data: ") and l != "data: [DONE]":
                            try: d = json.loads(l[6:]); yield d['choices'][0]['delta'].get('content', '')
                            except: pass
                else:
                    d = json.loads(resp.read()); yield d['choices'][0]['message'].get('content', '')
        except Exception as e: yield c(C.RED, f"✗ Error: {e}")

class AnthropicBackend:
    def __init__(self, api_key=None, model=None):
        self.api_key, self.model, self.tools_enabled = api_key or os.environ.get("ANTHROPIC_API_KEY"), model or "claude-sonnet-4-5", True
        self.is_oauth = self.api_key and "sk-ant-oat" in self.api_key
    @property
    def name(self): return f"anthropic:{self.model}({'oauth' if self.is_oauth else 'api'})"
    def is_ready(self): return bool(self.api_key)
    def generate(self, messages, system_prompt, max_tokens, temperature=0.7, stream=False):
        if not self.is_ready(): yield c(C.RED, "✗ Anthropic not ready"); return
        headers = {"Content-Type": "application/json", "anthropic-version": "2023-06-01"}
        if self.is_oauth:
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["anthropic-beta"] = "claude-code-20250219,oauth-2025-04-20,fine-grained-tool-streaming-2025-05-14,interleaved-thinking-2025-05-14"
        else: headers["x-api-key"] = self.api_key
        payload = {"model": self.model, "messages": messages[-20:], "max_tokens": max_tokens, "temperature": temperature, "system": system_prompt, "stream": stream}
        if self.tools_enabled: payload["tools"] = ANTHROPIC_TOOL_DEFS
        try:
            req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(payload).encode(), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=120) as resp:
                if stream:
                    for line in resp:
                        l = line.decode('utf-8').strip()
                        if l.startswith("data: "):
                            try:
                                d = json.loads(l[6:])
                                if d['type'] == 'content_block_delta': yield d['delta'].get('text', '')
                            except: pass
                else:
                    d = json.loads(resp.read()); yield "".join([b['text'] for b in d['content'] if b['type'] == 'text'])
        except Exception as e: yield c(C.RED, f"✗ Error: {e}")

# ── HyperClaw ─────────────────────────────────────────────────────────────────
class HyperClaw:
    COMMANDS = [("models", "Select model"), ("tokens", "Set tokens"), ("temp", "Set temp"), ("tools", "Toggle tools"), ("gpu", "Toggle GPU"), ("layers", "Set layers"), ("status", "Show state"), ("reset", "Clear context"), ("save", "Save convo"), ("load", "Load convo"), ("config", "Edit config"), ("clear-db", "Wipe session DB"), ("clear-errors", "Wipe error log"), ("council", "Forge persona (temp)"), ("council save", "Forge persona (permanent)"), ("system", "System info"), ("sessions", "List saved"), ("resume", "Load ID"), ("search", "Search hist"), ("summarize", "Create summary"), ("clear", "Clear screen"), ("about", "About"), ("quit", "Exit")]

    def __init__(self, config_path=None, resume_last=False, ephemeral=False):
        self.script_dir = Path(__file__).parent.resolve(); self.config = self.load_config(config_path or self.script_dir / "config.json")
        self.conversation, self.ephemeral, self.session_manager = [], ephemeral, SessionManager() if not ephemeral else None
        if self.session_manager:
            sid = self.session_manager.get_last_session_id() if resume_last else None
            if sid:
                msgs = self.session_manager.resume_session(sid)
                self.conversation = [{"role": m["role"], "content": m["content"]} for m in msgs]
                print(ts() + c(C.CYAN, f"✓ Resumed session {sid}"))
            else: self.session_manager.new_session(title=datetime.now().strftime("Session %Y-%m-%d %H:%M"))
        self.max_tokens, self.temperature, self.gpu_layers = self.config.get("max_tokens", 1024), self.config.get("temperature", 0.7), 33
        self.hyperion_bin = self.find_hyperion(); self.model_path = self.find_model(self.config.get("model"))
        self.backends = self._init_backends()
        self.active_backend = self.backends.get(self.config.get("active_backend", "mistral"), self.backends["mistral"])
        atexit.register(self._stop_server)
        h = Path.home() / ".hyperclaw_history"
        try: readline.read_history_file(h)
        except: pass
        atexit.register(readline.write_history_file, h)

    def _init_backends(self):
        api, s = self.config.get("apis", {}), self.config.get("socket_path", "/tmp/hyperion.sock")
        return {
            "local": LocalBackend(self.hyperion_bin, self.model_path, self.config), 
            "server": SocketBackend(s, self.model_path, self.config), 
            "anthropic": AnthropicBackend(api.get("anthropic",{}).get("api_key"), api.get("anthropic",{}).get("model")),
            "openai": OpenAIBackend("openai", api.get("openai",{}).get("api_key"), api.get("openai",{}).get("model")),
            "openrouter": OpenAIBackend("openrouter", api.get("openrouter",{}).get("api_key"), api.get("openrouter",{}).get("model")),
            "mistral": OpenAIBackend("mistral", api.get("mistral",{}).get("api_key"), api.get("mistral",{}).get("model"))
        }

    def _start_server(self):
        if not self.model_path: return
        s, b = Path(self.config["socket_path"]), self.hyperion_bin.parent / "model_server_socket"
        if s.exists(): s.unlink()
        print(ts() + c(C.YELLOW, f"🚀 Starting Titan Server for {self.model_path.name}..."))
        env = os.environ.copy(); env["HYPERION_GPU_LAYERS"] = str(self.gpu_layers)
        self.server_proc = subprocess.Popen([str(b), str(self.model_path), str(s)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        for _ in range(60):
            if s.exists(): self.active_backend = self.backends["server"] = SocketBackend(s, self.model_path, self.config); print(ts() + c(C.CYAN, "✓ Titan Server ready")); return
            time.sleep(0.5)

    def _stop_server(self):
        if hasattr(self, 'server_proc') and self.server_proc:
            self.server_proc.terminate()
            try:
                self.server_proc.wait(timeout=3)  # Wait for graceful shutdown
            except subprocess.TimeoutExpired:
                self.server_proc.kill()  # Force kill if it hangs
                self.server_proc.wait()
            self.server_proc = None
        s = Path(self.config["socket_path"])
        if s.exists(): s.unlink()
        time.sleep(0.1)  # Ensure socket cleanup completes

    def find_hyperion(self):
        for p in [self.script_dir / "hyperion" / "hyperion_generate", Path.home() / "hyperion/build/hyperion_generate", Path.home() / ".openclaw/workspace/hyperion/hyperion_generate"]:
            if p.exists(): return p.resolve()
        return None

    def find_model(self, name=None):
        dirs = [self.script_dir / "models", Path.home() / "Downloads/models", Path.home() / ".openclaw/workspace/models", Path.home() / "models", Path.home() / "hyperion/models"]
        if name:
            for d in dirs:
                if (d / name).exists(): return (d / name).resolve()
        for d in dirs:
            if d.is_dir():
                m = list(d.glob("*.gguf")) + list(d.glob("*.hyp"))
                if m: return m[0].resolve()
        return None

    def list_models(self):
        m, seen = [], set()
        for d in [self.script_dir / "models", Path.home() / "Downloads/models", Path.home() / ".openclaw/workspace/models", Path.home() / "models", Path.home() / "hyperion/models"]:
            if d.is_dir():
                for mp in list(d.glob("*.gguf")) + list(d.glob("*.hyp")):
                    rp = mp.resolve()
                    if rp not in seen: seen.add(rp); m.append((rp, rp.stat().st_size / (1024**3)))
        return sorted(m, key=lambda x: x[1])

    def load_config(self, p):
        d = {"repetition_penalty": 1.1, "max_tokens": 1024, "temperature": 0.7, "system_prompt": "You are HyperClaw, a helpful AI.", "active_backend": "server", "socket_path": "/tmp/hyperion.sock", "context_size": 8192}
        if os.path.exists(p): d.update(json.loads(Path(p).read_text()))
        return d

    def show_command_menu(self):
        if not shutil.which("fzf"): return
        e = [f"/{cn:10s}  {cd}" for cn, cd in self.COMMANDS]
        r = subprocess.run(["fzf", "--height=15", "--layout=reverse", "--border", "--prompt= Command > /"], input="\n".join(e), capture_output=True, text=True)
        if r.returncode == 0: self.handle_command(r.stdout.strip().split()[0])

    def handle_command(self, line):
        if line == "/": self.show_command_menu(); return
        p = line.split(); cmd = p[0].lstrip("/")
        if cmd in ["quit", "exit"]: sys.exit(0)
        elif cmd == "help": print_line(); [print(f"  {c(C.BLUE, f'/{cn:10s}')} {cd}") for cn, cd in self.COMMANDS]
        elif cmd == "models":
            print_line(); mlist = []
            for mp, sz in self.list_models(): mlist.append({"type": "local", "backend": "server", "display": f"{mp.name} ({sz:.1f}GB)", "data": mp})
            for n in ["mistral", "anthropic", "openrouter", "openai"]:
                if self.backends[n].is_ready(): mlist.append({"type": "cloud", "backend": n, "display": self.backends[n].name, "data": None})
            for i, m in enumerate(mlist, 1): print(f"  {c(C.BLUE, f'{i:2d}')} {c(C.WHITE, m['display'])}")
            sel = input(c(C.YELLOW, "\n  Select #: ")).strip()
            if sel.isdigit() and 0 < int(sel) <= len(mlist):
                m = mlist[int(sel)-1]
                if m["type"] == "local": self.model_path = m["data"]; self._stop_server(); self._start_server()
                else: self._stop_server(); self.active_backend = self.backends[m["backend"]]
        elif cmd == "tokens": val = input(f"  Tokens (current {self.max_tokens}): ").strip(); self.max_tokens = int(val) if val.isdigit() else self.max_tokens
        elif cmd == "temp": val = input(f"  Temp (current {self.temperature}): ").strip(); self.temperature = float(val) if val else self.temperature
        elif cmd == "tools":
            be = self.active_backend
            if hasattr(be, 'tools_enabled'):
                be.tools_enabled = not be.tools_enabled
                state = c(C.CYAN, "ON") if be.tools_enabled else c(C.GREY, "OFF")
                print(f"  Tools: {state}")
            else: print(c(C.YELLOW, "  ⚠ Tool calling not supported by this backend"))
        elif cmd == "gpu":
            self.gpu_layers = 0 if self.gpu_layers > 0 else 33
            state = c(C.CYAN, f"ON ({self.gpu_layers} layers)") if self.gpu_layers > 0 else c(C.GREY, "OFF (CPU only)")
            print(f"  GPU: {state}")
            if hasattr(self, 'server_proc') and self.server_proc: self._stop_server(); self._start_server()
        elif cmd == "layers":
            val = input(f"  GPU layers (current {self.gpu_layers}, 0=CPU only): ").strip()
            if val.isdigit(): self.gpu_layers = int(val); print(f"  GPU layers: {c(C.CYAN, str(self.gpu_layers))}")
            if hasattr(self, 'server_proc') and self.server_proc: self._stop_server(); self._start_server()
        elif cmd == "status":
            print_line()
            tools_on = getattr(self.active_backend, 'tools_enabled', False)
            tools_s = c(C.CYAN, "on") if tools_on else c(C.GREY, "off")
            gpu_s = c(C.CYAN, f"on ({self.gpu_layers} layers)") if self.gpu_layers > 0 else c(C.GREY, "off (CPU)")
            print(f"  Backend : {c(C.WHITE, self.active_backend.name)}")
            print(f"  Model   : {c(C.WHITE, self.model_path.name if self.model_path else 'none')}")
            print(f"  Tokens  : {c(C.WHITE, str(self.max_tokens))}  Temp: {c(C.WHITE, str(self.temperature))}")
            print(f"  Tools   : {tools_s}  GPU: {gpu_s}")
            print(f"  Turns   : {c(C.WHITE, str(len(self.conversation) // 2))}")
        elif cmd == "reset":
            self.conversation = []
            if self.session_manager: self.session_manager.new_session(title=datetime.now().strftime("Session %Y-%m-%d %H:%M"))
            print(c(C.CYAN, "  ✓ Context cleared"))
        elif cmd == "save":
            name = p[1] if len(p) > 1 else datetime.now().strftime("convo_%Y%m%d_%H%M%S")
            out_dir = self.script_dir / "conversations"; out_dir.mkdir(exist_ok=True)
            out_path = out_dir / f"{name}.json"
            out_path.write_text(json.dumps(self.conversation, indent=2))
            print(c(C.CYAN, f"  ✓ Saved {len(self.conversation)} messages → conversations/{name}.json"))
        elif cmd == "load":
            if len(p) < 2: print(c(C.YELLOW, "  Usage: /load <name>")); return
            name = p[1]; convo_dir = self.script_dir / "conversations"
            path = convo_dir / (name if name.endswith(".json") else f"{name}.json")
            if not path.exists(): print(c(C.RED, f"  ✗ Not found: {path}")); return
            self.conversation = json.loads(path.read_text())
            print(c(C.CYAN, f"  ✓ Loaded {len(self.conversation)} messages from {path.name}"))
        elif cmd == "config":
            editor = os.environ.get("EDITOR", "nano")
            cfg_path = self.script_dir / "config.json"
            if not cfg_path.exists():
                import shutil as _sh; _sh.copy(self.script_dir / "config.example.json", cfg_path)
            subprocess.run([editor, str(cfg_path)])
            self.config = self.load_config(cfg_path)
            self.backends = self._init_backends()
            print(c(C.CYAN, "  ✓ Config reloaded"))
        elif cmd == "clear-db":
            if not self.session_manager: print(c(C.YELLOW, "  ⚠ Ephemeral mode — no DB")); return
            confirm = input(c(C.YELLOW, "  Wipe all sessions? [y/N]: ")).strip().lower()
            if confirm == "y":
                db_path = Path.home() / ".hyperclaw" / "sessions.db"
                if db_path.exists(): db_path.unlink()
                self.session_manager = SessionManager()
                self.session_manager.new_session(title=datetime.now().strftime("Session %Y-%m-%d %H:%M"))
                print(c(C.CYAN, "  ✓ Session database wiped"))
            else: print(c(C.GREY, "  Cancelled"))
        elif cmd == "clear-errors":
            err_path = Path.home() / ".hyperclaw" / "errors.jsonl"
            if err_path.exists(): err_path.unlink(); print(c(C.CYAN, "  ✓ Error log cleared"))
            else: print(c(C.GREY, "  Error log is already empty"))
        elif cmd == "council":
            save_to_disk = len(p) > 1 and p[1] == "save"
            print(c(C.YELLOW, "\n  🔥 Summoning the Council of 12 Disruptors..."))
            council_instruction = """You are an orchestrator channeling a Council of 12 extreme historical disruptors:
Steve Jobs, Elon Musk, Napoleon Bonaparte, Ayn Rand, Nikola Tesla, Niccolò Machiavelli, 
Miyamoto Musashi, Marie Curie, Alexander the Great, Friedrich Nietzsche, Ada Lovelace, and Sun Tzu.

Your task is to write a NEW system prompt for an elite AI CLI tool called HyperClaw.
Discard "polite AI" tropes. Discard "balance." 
The new system prompt must force the AI to answer with uncompromising quality, 
first-principles logic, ruthless efficiency, and multidisciplinary synthesis.

Output ONLY the raw text for the new system prompt. No markdown formatting, no explanations."""
            print(f"  {c(C.GREY, 'Consulting ' + self.active_backend.name + ' to forge new persona...')}")
            new_prompt = "".join(self.active_backend.generate(
                [{"role": "user", "content": council_instruction}], 
                "You are an expert system prompt engineer.", 
                max_tokens=1000, 
                temperature=0.8, 
                stream=False
            )).strip()
            if new_prompt.startswith("```"): new_prompt = "\n".join(new_prompt.split("\n")[1:-1]).strip()
            self.config["system_prompt"] = new_prompt
            if save_to_disk:
                cfg_path = self.script_dir / "config.json"
                if cfg_path.exists():
                    with open(cfg_path, "r") as f: cfg_data = json.load(f)
                    cfg_data["system_prompt"] = new_prompt
                    with open(cfg_path, "w") as f: json.dump(cfg_data, f, indent=2)
                print(c(C.CYAN, "  ✓ Persona forged and saved to config.json"))
            else:
                print(c(C.CYAN, "  ✓ Persona forged (session only — use /council save to keep)"))
            print(f"\n  {c(C.GREY, 'Preview:')}\n  {c(C.WHITE, new_prompt[:300])}...\n")
        elif cmd == "clear": print_banner(len(self.list_models())); [print(f"  {c(C.BLUE, f'/{cn:10s}')} {cd}") for cn, cd in self.COMMANDS]
        elif cmd == "sessions":
            if not self.session_manager: print(c(C.YELLOW, "  ⚠ Ephemeral mode — no sessions")); return
            print_line(); sessions = self.session_manager.list_sessions()
            if sessions:
                for s in sessions: print(f"  {c(C.BLUE, str(s['id']))}  {c(C.WHITE, s['title'])}  {c(C.GREY, '(' + str(s['message_count']) + ' msgs)')}")
            else: print(c(C.GREY, "  No saved sessions yet"))
        elif cmd == "resume":
            if not self.session_manager: print(c(C.YELLOW, "  ⚠ Ephemeral mode — no sessions")); return
            sid = int(p[1]) if len(p) > 1 and p[1].isdigit() else None
            if not sid: print(c(C.YELLOW, "  Usage: /resume <id>")); return
            self.conversation = [{"role": m["role"], "content": m["content"]} for m in self.session_manager.resume_session(sid)]
            print(c(C.CYAN, f"  ✓ Resumed session {sid} ({len(self.conversation)} messages)"))
        elif cmd == "search":
            if not self.session_manager: print(c(C.YELLOW, "  ⚠ Ephemeral mode — no sessions")); return
            query = " ".join(p[1:])
            if not query: print(c(C.YELLOW, "  Usage: /search <query>")); return
            print_line(); results = self.session_manager.search_messages(query)
            if results: [print(f"  [{c(C.BLUE, str(r['session_id']))}] {c(C.GREY, r['role'])}: {r['content'][:80]}") for r in results]
            else: print(c(C.GREY, "  No results found"))
        elif cmd == "summarize":
            if not self.conversation: print(c(C.YELLOW, "  ⚠ Nothing to summarize")); return
            s = "".join(self.active_backend.generate(self.conversation, "Summarize this conversation in 3-5 sentences.", 500, 0.7, stream=False))
            if self.session_manager: self.session_manager.add_summary(s, len(self.conversation))
            print(c(C.CYAN, "\n  Summary:\n") + s)
        elif cmd == "system":
            print_line()
            try:
                cpu_model = subprocess.run("grep -m1 'model name' /proc/cpuinfo | cut -d: -f2", shell=True, capture_output=True, text=True).stdout.strip() or "Unknown"
                cpu_cores = subprocess.run("nproc", capture_output=True, text=True).stdout.strip()
                mem_info = {k.strip(): v.strip() for k, v in (l.split(':', 1) for l in open('/proc/meminfo') if ':' in l)}
                total_mb = int(mem_info.get('MemTotal', '0 kB').split()[0]) // 1024
                avail_mb = int(mem_info.get('MemAvailable', '0 kB').split()[0]) // 1024
                gpu = subprocess.run("lspci 2>/dev/null | grep -i 'vga\\|3d\\|display' | head -1 | sed 's/.*: //'", shell=True, capture_output=True, text=True).stdout.strip() or "Not detected"
                print(f"  CPU  : {c(C.WHITE, cpu_model)}  ({c(C.CYAN, cpu_cores)} cores)")
                print(f"  RAM  : {c(C.WHITE, f'{avail_mb}MB free')} / {c(C.CYAN, f'{total_mb}MB total')}")
                print(f"  GPU  : {c(C.WHITE, gpu)}")
                print(f"  Layers: {c(C.CYAN, str(self.gpu_layers))} ({'active' if self.gpu_layers > 0 else 'CPU only'})")
            except Exception as e: print(c(C.RED, f"  ✗ Error reading system info: {e}"))
        elif cmd == "about":
            print_line()
            print(f"  {c(C.CYAN, 'HyperClaw ⚡')} — Standalone Local AI Assistant")
            print(f"  {c(C.GREY, 'Break free from corporate control. Own your AI.')}")
            print(f"  {c(C.GREY, 'Local-first, cloud-fallback. No vendor lock-in.')}")

    def print_footer(self):
        """Print OpenClaw-style status footer"""
        tools_state = c(C.CYAN, "tools:on") if getattr(self.active_backend, 'tools_enabled', False) else c(C.GREY, "tools:off")
        turns = len(self.conversation) // 2

        # Approximate token usage (4 chars ≈ 1 token)
        context_tokens = sum(len(str(m.get('content', ''))) for m in self.conversation) // 4

        # Context window by backend
        backend_name = self.active_backend.name.lower()
        if "anthropic" in backend_name or "claude" in backend_name: context_limit = 200000
        elif "mistral" in backend_name: context_limit = 128000
        elif "openrouter" in backend_name: context_limit = 200000
        elif "local" in backend_name or "server" in backend_name: context_limit = self.config.get("context_size", 8192)
        else: context_limit = 8192

        tokens_used = f"{context_tokens//1000}k" if context_tokens > 1000 else str(context_tokens)
        tokens_limit = f"{context_limit//1000}k" if context_limit >= 1000 else str(context_limit)
        token_pct = int((context_tokens / context_limit) * 100) if context_limit > 0 else 0

        footer_parts = [
            c(C.CYAN, "hyperclaw"),
            c(C.WHITE, self.active_backend.name),
            tools_state,
            c(C.GREY, f"tokens {tokens_used}/{tokens_limit} ({token_pct}%)"),
            c(C.GREY, f"max_out:{self.max_tokens}"),
            c(C.GREY, f"temp:{self.temperature}"),
            c(C.GREY, f"turns:{turns}")
        ]
        print(f"\n{' | '.join(footer_parts)}\n")

    def run(self):
        print_banner(len(self.list_models())); self.handle_command("/help"); self.print_footer()
        if self.ephemeral: print(c(C.YELLOW, "  ⚠  Ephemeral mode — sessions will not be saved\n"))
        print(f"  {c(C.GREY, 'Tip:')} {c(C.CYAN, 'type / and press Enter')} {c(C.GREY, 'to open the command picker')}\n")
        while True:
            try:
                print_frame_top(); inp = input(f"{ts()}User: ").strip(); print_frame_bottom()
                if not inp: continue
                if inp.startswith("/"): self.handle_command(inp); continue
                self.conversation.append({"role": "user", "content": inp})
                if self.session_manager: self.session_manager.add_message("user", inp)
                print(f"{ts()}{c(C.CYAN, 'HyperClaw:')} ", end="", flush=True)
                full = ""
                for chunk in self.active_backend.generate(self.conversation, self.config["system_prompt"], self.max_tokens, self.temperature, stream=True):
                    print(chunk, end="", flush=True); full += chunk
                print(); self.conversation.append({"role": "assistant", "content": full})
                if self.session_manager:
                    self.session_manager.add_message("assistant", full)
                    if self.session_manager.should_summarize()[0]: self.handle_command("/summarize")
                self.print_footer()
            except (KeyboardInterrupt, EOFError): break

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="HyperClaw — local-first AI chat")
    parser.add_argument("--backend", help="Force a specific backend (server, anthropic, mistral, openrouter, openai)")
    parser.add_argument("--resume-last", action="store_true", help="Resume the most recent session")
    parser.add_argument("--ephemeral", action="store_true", help="Skip session saving")
    parser.add_argument("--prompt", metavar="TEXT", help="One-shot mode: send a single prompt, print response, exit. Use '-' to read from stdin.")
    args = parser.parse_args()

    # One-shot mode
    if args.prompt is not None:
        prompt_text = sys.stdin.read().strip() if args.prompt == "-" else args.prompt
        claw = HyperClaw(ephemeral=True)
        if args.backend and args.backend in claw.backends:
            claw.active_backend = claw.backends[args.backend]
        if claw.active_backend == claw.backends.get("server"):
            claw._start_server()
        claw.conversation.append({"role": "user", "content": prompt_text})
        for chunk in claw.active_backend.generate(
            claw.conversation, claw.config["system_prompt"],
            claw.max_tokens, claw.temperature, stream=False
        ):
            print(chunk, end="", flush=True)
        print()
        sys.exit(0)

    # Interactive mode
    claw = HyperClaw(resume_last=args.resume_last, ephemeral=args.ephemeral)
    if args.backend and args.backend in claw.backends:
        claw.active_backend = claw.backends[args.backend]
    if claw.active_backend == claw.backends.get("server"):
        claw._start_server()
    claw.run()
