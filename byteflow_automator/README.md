# ByteFlow Automator

A dedicated, general-purpose automation module for the ByteFlow system.

ByteFlow's core Agent stays **lightweight** — its job is thinking, planning, and talking. `byteflow_automator` handles the **doing**: opening files, running dev tools, executing shell commands, managing processes, and more.

---

## Architecture

```
ByteFlow (core)                    byteflow_automator/
┌─────────────────┐               ┌──────────────────────────────────────┐
│  Agent (brain)  │ ─── plans ──► │  Automator                           │
│  Memory         │               │  ├── tasks/files.py   (12 tasks)     │
│  Providers      │               │  ├── tasks/apps.py    (7 tasks)      │
│  Tools (light)  │               │  ├── devtools/dev.py  (23 tasks)     │
└─────────────────┘               │  └── system/system.py (13 tasks)     │
                                  └──────────────────────────────────────┘
```

**ByteFlow thinks. Automator acts.**

- The Agent's `plan()` decides what needs to happen
- The Automator's `TaskRegistry` holds all the callable automation tasks
- Tasks are registered as ByteFlow `Tool` objects on the Agent, so the brain can invoke them naturally
- Destructive operations always require a two-step confirmation (preview → confirm)

---

## Quick Start

```python
from byteflow_automator import Automator

# Direct task calls (no LLM needed)
auto = Automator()
auto.run_task("git_status", "~/myproject")
auto.run_task("pip_install", "requests")
auto.run_task("open_app", "vscode")
auto.run_task("system_info")

# Convenience shortcuts
auto.open("vscode")
auto.git("status", "~/myproject")
auto.shell("ls -la ~/projects")
auto.install("flask")
auto.new_project("my-api", kind="python")
auto.edit("~/myproject", editor="vscode")
```

### With ByteFlow Brain (natural language)

```python
from byteflow_automator import Automator
from byteflow.providers.ollama_provider import OllamaProvider

provider = OllamaProvider(model="llama2")
auto = Automator(provider=provider)

# Plain English automation
auto.run("open vscode in ~/myproject and show git status")
auto.run("install requests and flask, then run main.py")
auto.run("create a python project called my-api in ~/projects")
auto.run("what processes are using the most CPU?")
auto.run("clone https://github.com/user/repo into ~/projects")
```

---

## CLI

```bash
# List all tasks
python -m byteflow_automator list

# Run any task
python -m byteflow_automator git_status ~/myproject
python -m byteflow_automator pip_install requests
python -m byteflow_automator open_app vscode
python -m byteflow_automator run_command "ls -la"
python -m byteflow_automator system_info
python -m byteflow_automator scaffold_python_project my-api ~/projects
python -m byteflow_automator check_tools git node docker python3

# Get info about a task
python -m byteflow_automator info git_status

# See all capabilities
python -m byteflow_automator capabilities
```

---

## All Tasks

### Files (12 tasks)
| Task | Description |
|------|-------------|
| `open_file` | Open a file with its default OS app |
| `read_file` | Read and return contents of a text file |
| `write_file` | Write text content to a file |
| `append_file` | Append text to a file |
| `list_folder` | List files in a folder with glob pattern |
| `search_files` | Search files by name keyword |
| `file_info` | Get metadata (size, modified date, type) |
| `create_folder` | Create a folder and any missing parents |
| `preview_delete` | Preview deletion (dry run, returns token) |
| `preview_move` | Preview move (dry run, returns token) |
| `preview_copy` | Preview copy (dry run, returns token) |
| `confirm_file_op` | Execute a confirmed destructive operation |

### Apps (7 tasks)
| Task | Description |
|------|-------------|
| `open_app` | Launch an app or website by shortcut name |
| `open_url` | Open a URL in the default browser |
| `open_in_editor` | Open a file/folder in a code editor |
| `list_app_shortcuts` | List all known shortcut names |
| `read_clipboard` | Return current clipboard text |
| `write_clipboard` | Copy text to the clipboard |
| `notify` | Send a desktop notification |

**Known shortcuts:** `vscode`, `cursor`, `pycharm`, `chrome`, `firefox`, `terminal`, `docker`, `postman`, `slack`, `discord`, `zoom`, `notion`, `github`, `stackoverflow`, `gmail`, `drive`, `figma`, `chatgpt`, `claude`, and more.

### Dev Tools (23 tasks)

**Git:** `git_status`, `git_log`, `git_diff`, `git_branch`, `git_pull`, `git_add_commit`, `git_clone`, `git_init`

**Python:** `pip_install`, `pip_list`, `pip_freeze`, `python_run`, `create_venv`

**Node:** `npm_install`, `npm_run`, `npm_list`, `node_run`

**Docker:** `docker_ps`, `docker_images`, `docker_logs`, `docker_compose_up`, `docker_compose_down`

**Scaffolding:** `scaffold_python_project`, `scaffold_node_project`

### System (13 tasks)
| Task | Description |
|------|-------------|
| `run_command` | Execute any shell command |
| `run_script` | Run a script file (.py, .sh, .js...) |
| `system_info` | OS, CPU, memory, disk info |
| `list_processes` | List running processes |
| `kill_process` | Terminate a process by name or PID |
| `get_env` | Get environment variable(s) |
| `set_env` | Set an environment variable |
| `which` | Find path of a command-line tool |
| `check_tools` | Check if tools are installed |
| `current_time` | Return current date and time |
| `run_after_delay` | Schedule a command (background) |
| `ping` | Ping a host |
| `http_get` | HTTP GET request |

---

## Safety Design

Destructive file operations (delete, move, copy) always require two steps:

```python
# Step 1: preview (dry run, safe)
result = auto.run_task("preview_delete", "~/old_folder")
# → "DRY RUN: Would delete '~/old_folder'... confirm_file_op('a1b2')"

# Step 2: confirm (human must do this explicitly)
result = auto.run_task("confirm_file_op", "a1b2")
# → "Deleted: ~/old_folder"
```

The ByteFlow brain cannot skip this — there's no argument to perform the action in one shot. The confirmation token only exists after a preview.

Similarly, `kill_process` is marked `safe=False` and won't be auto-executed by the planner.

---

## Adding Custom Tasks

```python
from byteflow_automator.registry import AutomationTask, register_task

def my_deploy(project_path: str) -> str:
    """Deploy a project."""
    import subprocess
    result = subprocess.run(["./deploy.sh"], cwd=project_path, capture_output=True, text=True)
    return result.stdout or result.stderr

register_task(AutomationTask(
    name="my_deploy",
    func=my_deploy,
    description="deploy a project using its deploy.sh script",
    category="devtools",
    example="my_deploy('~/myproject')",
))

# Now it's available everywhere
auto = Automator()
auto.run_task("my_deploy", "~/myproject")
```

---

## Project Structure

```
byteflow_automator/
├── __init__.py          # Automator, TaskRegistry exports
├── __main__.py          # CLI entrypoint
├── automator.py         # Main Automator class (ByteFlow bridge)
├── registry.py          # TaskRegistry, AutomationTask dataclass
├── examples.py          # Full usage examples
├── tasks/
│   ├── files.py         # File system tasks (12)
│   └── apps.py          # App/URL/clipboard tasks (7)
├── devtools/
│   └── dev.py           # Git, pip, npm, docker, scaffolding (23)
├── system/
│   └── system.py        # Shell, processes, env, network (13)
└── utils/               # Shared helpers (extensible)
```

---

## Dependencies

Built-in Python only for core functionality. Optional extras:
- `psutil` — CPU/memory/process info: `pip install psutil`
- `pyperclip` — Clipboard support: `pip install pyperclip`
- `plyer` — Desktop notifications on Windows: `pip install plyer`

---

## Why a Separate Module?

ByteFlow's Agent is designed to be lean: memory, chat, planning, tools. If automation logic lived there, it would bloat with OS-specific code, subprocess calls, platform checks, and dependency management.

`byteflow_automator` is the dedicated automation layer:
- Clean separation of concerns
- Easy to extend with new task categories
- Can run standalone (no LLM) or brain-directed (with ByteFlow Agent)
- Safe by design (dry runs, confirmation tokens, safe flags)
- Works on Windows, macOS, and Linux
