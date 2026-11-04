---
name: recorder-connection
description: Diagnose why the Recorder tools are missing or failing. Use when the user asks about their recordings but no recorder tools (list_recordings, search_recordings, get_recording) are available, or when a recorder tool call fails with a connection error.
---

# Recorder connection check

Run this and relay its output to the user in their own language:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/recorder/recorder_mcp.py" status
```

Then:

- Put any `http://127.0.0.1:…` link on its own line so the user can click it.
- If a link is printed, say it stays valid for 10 minutes and that pairing happens on the iPhone under Recorder → Settings → LAN Access.
- Do not retry the recorder tools while the check reports the app is unreachable.
- Do not try to read recordings yourself through Bash, files, or the network.
