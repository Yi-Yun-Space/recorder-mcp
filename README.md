# FrameMemo MCP plugin

Lets Claude Code read and summarize the recordings stored in the **FrameMemo** iPhone app, over your local network.

## Supported agent

**This release supports MCP access through Claude Code on Mac only.** Other agents are not supported in this release. This limitation applies to the MCP connection, not the providers you can configure for Ask AI inside the FrameMemo iPhone app.

## Install

Open a Claude Code session and send this message:

> Install the FrameMemo plugin and show me the pairing code: https://github.com/Yi-Yun-Space/recorder-mcp

Claude Code adds the marketplace, installs the plugin, and runs its pairing step. Scan the code it shows with **Add computer** on the iPhone.

Then **open a new session**. Plugin tools only load when a session starts.

## Pair the iPhone

Pairing runs during install. If that was skipped, the first session that runs the plugin opens a pairing page in your browser. On the iPhone:

1. Open FrameMemo → Settings → Agent Access and turn on **Allow agent access**. Keep FrameMemo open in the foreground.
2. Tap **Add computer** and scan the code shown on the Mac.
3. Tap **Allow**.

The page changes to "Paired with …" once the phone is done.

On the simulator there is no camera: tap **Add computer**, then paste the pairing link shown under the code on the Mac page. You can also choose **Enter pairing link** on the scanner screen when using an iPhone.

## Requirements

- Claude Code on a Mac.
- The iPhone and the Mac on the same trusted local network, with local network access allowed for FrameMemo.
- `python3` on the Mac (comes with the Xcode Command Line Tools).
- FrameMemo open on the iPhone, with **Allow agent access** enabled, while you query.

## Revoke a computer

In FrameMemo → Settings → Agent Access, swipe a paired computer to remove it. That computer's next request is rejected, and it opens a fresh pairing page.

## When the recordings can't be reached

Just ask Claude Code about your recordings. If the tools are missing or the app is unreachable, the plugin's connection check reports what happened, including a pairing code if re-pairing would help. Ask Claude to *check the FrameMemo connection* if you want the report from an otherwise unrelated question.

## Troubleshooting

Check the phone side directly from the same Wi-Fi:

```bash
curl -H "Authorization: Bearer <device token>" http://<iphone-ip>:8765/health
```

- Connection refused: the app is backgrounded or the toggle is off. Bring the app to the foreground.
- 401: this computer was revoked or the pairing is stale. Pair again.
- Works from `127.0.0.1` in the simulator but not from a device: confirm both are on the same Wi-Fi and the router is not isolating clients.

Pairing settings live in `~/.config/recorder-mcp/config.json` (mode 0600).

## Manual setup

To skip the pairing page and write the settings directly:

```bash
python3 "<plugin root>/recorder_mcp.py" set --url http://<iphone-ip>:8765 --token <device token>
```

The app only issues per-device tokens during pairing, so this is mainly useful when testing the local connection with a known token.

## Installing from a terminal

```bash
claude plugin marketplace add Yi-Yun-Space/recorder-mcp
claude plugin install recorder@recorder-marketplace
```

Install and enable it per user (`--scope user` is the default for marketplaces), not per project, so it is available in every session.

## Layout

- `.claude-plugin/marketplace.json` — the marketplace this repository publishes.
- `recorder/` — the plugin itself: the MCP server and the connection-check skill.
