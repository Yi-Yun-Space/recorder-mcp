# Recorder MCP plugin

Lets Claude Code read and summarize the recordings stored in the **Recorder** iPhone app, over your local network.

## Install

Open a Claude Code session and send this message:

> Install the recorder plugin: https://github.com/Yi-Yun-Space/recorder-mcp

Claude Code adds the marketplace and installs the plugin for you.

Then **start a new session**. Plugin tools only load when a session starts — in the terminal you can run `/reload-plugins` instead of restarting.

## Pair the iPhone

The first session that runs the plugin opens a pairing page in your browser. On the iPhone:

1. Open Recorder → Settings → LAN Access and turn on **Enable**. Keep that screen open.
2. Tap **Add computer** and scan the code shown on the Mac.
3. Tap **Allow**.

The page changes to "Paired with …" once the phone is done.

## Requirements

- The iPhone and the Mac on the same Wi-Fi network.
- `python3` on the Mac (comes with the Xcode Command Line Tools).
- Recorder open on the iPhone, with LAN Access enabled, while you query.

## When the recordings can't be reached

Just ask Claude about your recordings. If the tools are missing or the app is unreachable, the plugin's connection check runs and reports what happened, including a pairing page link if re-pairing would help. Ask Claude to *check the recorder connection* if you want the report from an otherwise unrelated question.

## Installing from a terminal

```bash
claude plugin marketplace add Yi-Yun-Space/recorder-mcp
claude plugin install recorder@recorder-marketplace
```

Install and enable it per user (`--scope user` is the default for marketplaces), not per project, so it is available in every session.

## Layout

- `.claude-plugin/marketplace.json` — the marketplace this repository publishes.
- `recorder/` — the plugin itself: the MCP server, the connection-check skill, and its own README.
