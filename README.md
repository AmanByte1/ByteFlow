# ByteFlow v2.0

An AI-powered desktop assistant you control from your phone.
ByteFlow runs on your laptop — your phone is just the remote.

---

## Quick Start (Windows)

**Option A — PowerShell (recommended):**
```powershell
.\START.ps1
```

**Option B — Batch file:**
```bat
START.bat
```

**Option C — Manual (2 terminals):**
```bash
# Terminal 1
python -m byteflow.api_server --model llama3

# Terminal 2
python -m byteflow_frontend
```

Then scan the QR code or open the URL shown on your phone.

---

## Requirements

- Python 3.10+
- Ollama — ollama.com — with at least one model

```bash
ollama pull llama3
```

```bash
pip install fastapi "uvicorn[standard]" httpx pydantic qrcode psutil pyperclip
```

---

## Phone UI — 7 Tabs

| Tab | What it does |
|-----|-------------|
| 💬 Chat | Talk to ByteFlow — Auto, Chat, Code, Search modes |
| 🎙️ Voice | Tap the orb, speak, hear the response |
| 📁 Files | Browse and read files on your laptop |
| 🧑‍💻 Code | Write, fix, review, run code in any language |
| ⏰ Tasks | Schedule shell commands |
| 🧩 Plugins | Browse and install plugins |
| 📡 Devices | See all connected devices |

---

## Using Different Models

```bash
python -m byteflow.api_server --model llama3
python -m byteflow.api_server --model my-buddy
python -m byteflow.api_server --model mistral
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| model not found | ollama pull llama3 |
| Phone can't connect | Same WiFi? Use IP shown in terminal |
| Connection refused | Run ollama serve first |
| Core offline | python -m byteflow.api_server |
