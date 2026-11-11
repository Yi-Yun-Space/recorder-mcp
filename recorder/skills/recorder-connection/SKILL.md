---
name: recorder-connection
description: Diagnose why the FrameMemo tools are missing or failing. Use when the user asks about their recordings but no recorder tools (list_recordings, search_recordings, get_recording) are available, or when a recorder tool call fails with a connection error.
---

# FrameMemo connection check

Run this and relay its output to the user in their own language:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/recorder_mcp.py" status
```

Then:

- Put any `http://127.0.0.1:…` link on its own line so the user can click it.
- If the output names a `QR image:` path and that file exists, send that image **as the last step of your reply** — all text first — and set `display` to `render`: the default attachment card is only a thumbnail and cannot be scanned.
- Say the code stays valid for 10 minutes, and that pairing happens on the iPhone under FrameMemo → Settings → LAN Access.
- Always finish by telling the user to open a new session before asking about recordings — the plugin's tools only load when a session starts.
- Do not retry the recorder tools while the check reports the app is unreachable.
- Do not try to read recordings yourself through Bash, files, or the network.
