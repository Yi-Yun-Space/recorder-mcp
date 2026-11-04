# Recorder MCP plugin

Lets Claude Code read transcripts stored in the Recorder iPhone app over the local network.

## Install

```bash
claude plugin marketplace add /absolute/path/to/mcp-plugin
claude plugin install recorder@recorder-marketplace
```

Restart Claude Code after installing.

## Pair

No command to run. The first time the plugin starts without a saved pairing, it opens a pairing page on your Mac automatically.

On the iPhone:

1. Open Recorder → Settings (the gear on the home screen) → LAN Access and turn on **Enable**. Keep that screen open while you use the Mac.
2. Tap **Add computer** and scan the code shown on the Mac.
3. Tap **Allow**.

On the simulator there is no camera: tap **Add computer**, then paste the pairing link shown under the code on the Mac page.

The page updates to "Paired with …" once the phone is done.

## Revoke

In Recorder → Settings → LAN Access → **Paired computers**, swipe a computer to remove it. That computer's next request is rejected, and Claude Code opens a fresh pairing page automatically.

## Tools

- `search_transcripts` — keyword search across transcripts
- `list_recordings` — newest recordings first
- `get_recording` — full timestamped transcript for one recording

## Troubleshooting

Check the phone side directly from the same Wi-Fi:

```bash
curl -H "Authorization: Bearer <device token>" http://<iphone-ip>:8765/health
```

- Connection refused: the app is backgrounded or the toggle is off. Bring the app to the foreground.
- 401: this computer was revoked or the pairing is stale. The plugin opens a pairing page; pair again.
- Works from `127.0.0.1` in the simulator but not from a device: confirm both are on the same Wi-Fi and the router is not isolating clients.

Pairing settings live in `~/.config/recorder-mcp/config.json` (mode 0600).

## Manual setup

For troubleshooting you can skip the pairing page and write the settings directly:

```bash
python3 recorder_mcp.py set --url http://<iphone-ip>:8765 --token <device token>
```

The app only issues per-device tokens during pairing, so this is mainly useful for testing the gateway against a known token.
