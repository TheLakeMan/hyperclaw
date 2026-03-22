HyperClaw - Standalone Local AI Assistant
==========================================

Setup on laptop (thelakeman@192.168.1.129):

1. Extract to home directory:
   cd ~
   cp /path/to/usb/hyperclaw-clean.tar.gz .
   tar xzf hyperclaw-clean.tar.gz
   mv hyperclaw-clean hyperclaw

2. Make executable:
   chmod +x ~/hyperclaw/hyperclaw.py

3. Run:
   cd ~/hyperclaw
   ./hyperclaw.py

Auto-detects:
- Hyperion at ~/hyperion/build/ (already installed)
- All 7 models (already present)
- OBLITERATUS at ~/OBLITERATUS-main/ (already there)

Commands:
- /models    : List all 7 models
- /model N   : Select model by number
- /paths     : Show search paths
- /help      : All commands
- /exit      : Quit

No hardcoded paths. Everything dynamic.

⚡ Stay free.
