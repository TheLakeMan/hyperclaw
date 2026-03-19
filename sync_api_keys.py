#!/usr/bin/env python3
"""Sync API keys from OpenClaw config to HyperClaw config"""
import json
from pathlib import Path

openclaw_config = Path.home() / ".openclaw" / "openclaw.json"
hyperclaw_config = Path.home() / "hyperclaw" / "config.json"

# Load configs
with open(openclaw_config) as f:
    oc = json.load(f)
with open(hyperclaw_config) as f:
    hc = json.load(f)

# Extract API keys from OpenClaw
providers = oc.get("models", {}).get("providers", {})

# Update HyperClaw config
updated = False

# Anthropic
anthropic_key = providers.get("anthropic", {}).get("apiKey")
if anthropic_key:
    hc["apis"]["anthropic"]["api_key"] = anthropic_key
    updated = True
    print(f"✓ Anthropic API key synced")
else:
    print("✗ Anthropic API key not found in OpenClaw config")
    print("  You need to add it to OpenClaw first:")
    print("  openclaw config.patch models.providers.anthropic.apiKey YOUR_KEY_HERE")

# OpenRouter (check if it matches)
openrouter_key = providers.get("openrouter", {}).get("apiKey")
if openrouter_key:
    if hc["apis"]["openrouter"]["api_key"] != openrouter_key:
        hc["apis"]["openrouter"]["api_key"] = openrouter_key
        updated = True
        print(f"✓ OpenRouter API key updated")
    else:
        print(f"  OpenRouter API key already synced")

# Mistral (check if it matches)
mistral_key = providers.get("mistral", {}).get("apiKey")
if mistral_key:
    if hc["apis"]["mistral"]["api_key"] != mistral_key:
        hc["apis"]["mistral"]["api_key"] = mistral_key
        updated = True
        print(f"✓ Mistral API key updated")
    else:
        print(f"  Mistral API key already synced")

# Save if updated
if updated:
    with open(hyperclaw_config, 'w') as f:
        json.dump(hc, f, indent=2)
    print(f"\n✓ HyperClaw config updated: {hyperclaw_config}")
else:
    print(f"\n  No changes needed")
