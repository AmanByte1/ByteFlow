# ByteFlowPet

ByteFlowPet is a separate desktop-pet project designed to sit on top of your screen, move around by itself, remember how you treat it, and use your ByteFlow framework as its brain.

It is intentionally separate from ByteFlow. ByteFlowPet imports ByteFlow if it is installed, or if you point `PYTHONPATH` at your ByteFlow source folder.

## What It Does

- Shows an always-on-top movable pet window.
- Pet wanders around your desktop.
- Click the pet to open the control panel.
- Chat messages go through ByteFlow when available.
- Pet remembers mood, trust, energy, age, learned actions, and conversation notes.
- You can teach simple actions, like:
  - `open calculator`
  - `open youtube`
  - `click 500 300`
  - `say hello`

## Setup

From this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

To use your existing ByteFlow source from the inspected zip:

```powershell
$env:PYTHONPATH="C:\Users\aman\Documents\Codex\2026-07-09\this-is-a-my-ai-framework\work\byteflow-source\ByteFlow"
byteflow-pet
```

If you have ByteFlow installed normally, just run:

```powershell
byteflow-pet
```

For mouse clicking actions, install the optional desktop control package:

```powershell
python -m pip install -e ".[desktop-control]"
```

## Teaching Examples

Open the panel, then use the "Teach action" fields:

| Action name | Command |
| --- | --- |
| calc | open calculator |
| yt | open youtube |
| note | open notepad |
| click-center | click 960 540 |
| greet | say I am ready |

After teaching, type:

```text
do calc
do yt
do click-center
```

## ByteFlow Brain

The bridge tries to create:

```python
Agent(provider=OllamaProvider(model="llama3"), memory_path="data/byteflow_memory.json")
```

Then it registers ByteFlow builtin tools and desktop tools if those modules are available.

If ByteFlow or Ollama is not available, the pet still runs with local memory and trained actions.

## Safety

The pet can open apps and URLs. Mouse clicking is disabled unless `pyautogui` is installed. There is no autonomous destructive file operation in this project.
