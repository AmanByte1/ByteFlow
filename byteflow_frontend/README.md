# ByteFlow Frontend

Control ByteFlow from your **phone, tablet, or any browser** — while it runs on your laptop.

No app download. No cloud. Just open a browser on your phone and connect over WiFi.

---

## How it works

```
Your Laptop                          Your Phone (or any device)
┌─────────────────────────────┐      ┌──────────────────────┐
│  byteflow_frontend server   │ WiFi │  Browser             │
│  ├── ByteFlow Agent (brain) │◄────►│  Jarvis UI           │
│  ├── byteflow_automator     │      │  Voice input         │
│  └── All AI providers       │      │  Real-time updates   │
└─────────────────────────────┘      └──────────────────────┘
```

ByteFlow stays on your laptop. The phone is just the controller.

---

## Quick Start

### 1. Install dependencies

```bash
cd ByteFlow/byteflow_frontend
pip install -r requirements.txt
```

### 2. Start the server (on your laptop)

```bash
# From ByteFlow root folder:
python -m byteflow_frontend

# Or with options:
python -m byteflow_frontend --port 7860 --model mistral
python -m byteflow_frontend --model llama2 --open   # also opens browser
```

### 3. Connect from your phone

The terminal will print something like:

```
=======================================================
  ByteFlow Frontend — Jarvis for your phone
=======================================================
  Local:   http://localhost:7860
  Phone:   http://192.168.1.45:7860
  Model:   llama2  |  Provider: ollama
=======================================================

  Scan this QR code with your phone:

  ██████████████  ██  ██████████████
  ...
```

**Scan the QR code** or open `http://192.168.1.XX:7860` on your phone's browser.

> Your phone and laptop must be on the **same WiFi network**.

---

## Features

### 5 Modes (tabs in the UI)

| Mode | What it does |
|------|-------------|
| ⚡ **Jarvis** | Full autonomous mode — ByteFlow plans and acts |
| 💬 **Chat** | Pure conversation with the AI |
| 🐍 **Code** | Generate and execute Python code |
| 🔍 **Search** | Web search + AI summary |
| 🤖 **Automate** | Direct automation tasks (browse + run) |

### Voice Input
Tap the 🎤 mic button → speak → ByteFlow answers.  
Uses the Web Speech API built into your phone's browser.

### Automation Panel
In **Automate** mode, all 55+ automation tasks appear in a browsable panel:
- Tap a task to fill it into the input
- Or type naturally: `git status ~/myproject`
- Or describe in plain English: `open vscode and show git status`

### Real-time Updates
WebSocket connection keeps the UI in sync. When ByteFlow is thinking, you see live dots. Results appear as soon as they're ready.

### Quick Actions bar
One-tap shortcuts: System Info, Git Status, Open VSCode, Time, Weather, Capabilities.

---

## API Endpoints

You can also call ByteFlow directly from anything that can make HTTP requests (scripts, Shortcuts app, IFTTT, etc.):

```bash
# Chat
curl -X POST http://192.168.1.45:7860/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "what time is it", "mode": "run"}'

# Run automation task
curl -X POST http://192.168.1.45:7860/api/automate \
  -H "Content-Type: application/json" \
  -d '{"task": "git_status", "args": ["~/myproject"]}'

# Natural language automation
curl -X POST http://192.168.1.45:7860/api/automate/nl \
  -H "Content-Type: application/json" \
  -d '{"goal": "open vscode in my project folder"}'

# List all automation tasks
curl http://192.168.1.45:7860/api/tasks

# Server status
curl http://192.168.1.45:7860/api/status

# Conversation memory
curl http://192.168.1.45:7860/api/memory

# Learned profile facts
curl http://192.168.1.45:7860/api/profile
```

---

## WebSocket (real-time)

Connect to `ws://192.168.1.45:7860/ws` for real-time events:

```javascript
const ws = new WebSocket('ws://192.168.1.45:7860/ws');

// Send a chat message
ws.send(JSON.stringify({
  event: 'chat',
  data: { message: 'hello', mode: 'run' }
}));

// Receive events: connected, thinking, response, automate_result, error
ws.onmessage = e => {
  const { event, data } = JSON.parse(e.data);
  console.log(event, data);
};
```

---

## CLI Options

```
python -m byteflow_frontend [options]

  --host      Host to bind (default: 0.0.0.0 = all interfaces)
  --port      Port number (default: 7860)
  --model     LLM model name (default: llama2)
  --provider  AI provider (default: ollama)
  --open      Open browser automatically on launch
```

---

## Project Structure

```
byteflow_frontend/
├── __init__.py          # Package entry
├── __main__.py          # CLI launcher (python -m byteflow_frontend)
├── server.py            # FastAPI server + all endpoints + WebSocket
├── requirements.txt     # Dependencies
├── README.md            # This file
└── static/
    └── index.html       # Full Jarvis UI (phone-optimised)
```

---

## Tips

- **iPad/tablet**: works great, full-width layout
- **Desktop browser**: also works, just narrow the window for the phone feel  
- **iPhone**: tap the mic, speak naturally — it auto-sends when you finish
- **Android**: same, Chrome has the best Speech API support
- **Keep terminal open**: the server runs in your terminal; closing it stops ByteFlow
- **Firewall**: if your phone can't connect, check that port 7860 is allowed on your laptop's firewall
