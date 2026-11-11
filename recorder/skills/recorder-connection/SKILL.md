---
name: recorder-connection
description: Diagnose why the FrameMemo tools are missing or failing. Use when the user asks about their recordings but no recorder tools (list_recordings, search_recordings, get_recording) are available, or when a recorder tool call fails with a connection error.
---

# FrameMemo connection check

Run this and relay its output:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/recorder_mcp.py" status
```

Then reply in English — even when the user writes in another language — in this order, and nothing else:

1. **One line:** the pairing code is ready and valid for 10 minutes.
2. **One line, the only action:** on the iPhone, FrameMemo → Settings → Agent Access → turn on **Allow agent access** → **Add computer** → scan the code → **Allow**. Say that the code is in the Read row above and that clicking that row expands it to full size. State the Settings path once — never again in a heading or a second paragraph.
3. **One fallback, only if that row cannot be expanded:** open the `http://127.0.0.1:…` link on its own line and use the code on that page.
4. **Only when the recorder tools are missing in this session** — it started before the plugin was installed — add one line asking the user to open a new session. If the tools are already available here, do not mention it.
5. **Last:** read the `QR image:` file with the Read tool: the code lands in a collapsed tool row that the user expands. Do not copy it into the working directory, and do not send it as a file attachment — that card shows only a blank thumbnail.

Do not offer a "copy and paste the link into the app" path — the user has an iPhone and scans the code. Do not summarise what the plugin does or how you reviewed its source; the user is waiting to scan.
Do not retry the recorder tools while the check reports the app is unreachable.
Do not try to read recordings yourself through Bash, files, or the network.
