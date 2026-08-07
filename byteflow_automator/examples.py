"""
ByteFlow Automator - Usage Examples
====================================
Demonstrates all automation categories: files, apps, devtools, system.
Also shows integration with the ByteFlow brain for natural language automation.
"""

from byteflow_automator import Automator

auto = Automator()  # No provider = direct task calls only


# ─────────────────────────────────────────────────────────────────────────────
# 1. CAPABILITIES - see what's available
# ─────────────────────────────────────────────────────────────────────────────

print("=" * 60)
print("1. ALL CAPABILITIES")
print("=" * 60)
print(auto.capabilities())


# ─────────────────────────────────────────────────────────────────────────────
# 2. FILE AUTOMATION
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("2. FILE AUTOMATION")
print("=" * 60)

# Write a file
result = auto.run_task("write_file", "/tmp/automator_test.txt", "Hello from ByteFlow Automator!\nLine 2.\n")
print("write_file:", result)

# Read it back
result = auto.run_task("read_file", "/tmp/automator_test.txt")
print("read_file:", result)

# Get file info
result = auto.run_task("file_info", "/tmp/automator_test.txt")
print("file_info:", result)

# Append to it
result = auto.run_task("append_file", "/tmp/automator_test.txt", "Appended line.\n")
print("append_file:", result)

# List files in /tmp matching a pattern
result = auto.run_task("list_folder", "/tmp", "*.txt")
print("list_folder (*.txt):", result[:5], "..." if len(result) > 5 else "")

# Search for files by keyword
result = auto.run_task("search_files", "/tmp", "automator")
print("search_files:", result)

# Create a folder
result = auto.run_task("create_folder", "/tmp/automator_demo_dir")
print("create_folder:", result)

# Preview delete (dry run - no token needed to be confirmed)
result = auto.run_task("preview_delete", "/tmp/automator_test.txt")
print("preview_delete:", result)


# ─────────────────────────────────────────────────────────────────────────────
# 3. APP SHORTCUTS
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("3. APP SHORTCUTS")
print("=" * 60)

# List known shortcuts
result = auto.run_task("list_app_shortcuts")
print("Known shortcuts:", result[:15], "...")

# Clipboard
auto.run_task("write_clipboard", "ByteFlow Automator rocks!")
result = auto.run_task("read_clipboard")
print("Clipboard:", result)

# Open an app (commented out - would actually open something on your desktop)
# result = auto.open("vscode")
# result = auto.open("https://github.com")
# result = auto.run_task("notify", "ByteFlow", "Automation complete!")


# ─────────────────────────────────────────────────────────────────────────────
# 4. DEV TOOLS - Git
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("4. DEV TOOLS - Git")
print("=" * 60)

# Use current directory (must be a git repo to get meaningful output)
result = auto.git("status", ".")
print("git status:\n", result[:300])

result = auto.git("log", ".")
print("\ngit log:\n", result[:300])

result = auto.git("branch", ".")
print("\ngit branch:\n", result[:200])


# ─────────────────────────────────────────────────────────────────────────────
# 5. DEV TOOLS - Python
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("5. DEV TOOLS - Python/pip")
print("=" * 60)

result = auto.run_task("pip_list")
lines = result.splitlines()
print(f"pip list ({len(lines)} packages):\n", "\n".join(lines[:10]), "\n...")

result = auto.install("requests")  # shortcut for pip_install
print("pip install requests:", result[:200])


# ─────────────────────────────────────────────────────────────────────────────
# 6. DEV TOOLS - Project scaffolding
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("6. PROJECT SCAFFOLDING")
print("=" * 60)

result = auto.new_project("demo-app", kind="python", path="/tmp")
print("scaffold_python_project:", result)

result = auto.run_task("list_folder", "/tmp/demo-app", recursive=True)
print("Project files created:", result)

result = auto.new_project("demo-node-app", kind="node", path="/tmp")
print("scaffold_node_project:", result)


# ─────────────────────────────────────────────────────────────────────────────
# 7. SYSTEM INFO & SHELL
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("7. SYSTEM INFO & SHELL")
print("=" * 60)

result = auto.run_task("system_info")
print("system_info:", result)

result = auto.run_task("check_tools", "git", "python3", "node", "docker", "code")
print("check_tools:", result)

result = auto.run_task("current_time")
print("current_time:", result)

result = auto.shell("echo 'Hello from shell!'")
print("shell command:", result)

result = auto.run_task("which", "python3")
print("which python3:", result)

result = auto.run_task("get_env", "HOME")
print("get_env HOME:", result)


# ─────────────────────────────────────────────────────────────────────────────
# 8. HISTORY
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("8. EXECUTION HISTORY")
print("=" * 60)

history = auto.history(5)
print(f"Last {len(history)} operations:")
for entry in history:
    print(f"  [{entry['time'][:19]}] {entry['task']}({entry['args']}) -> {str(entry['result'])[:60]}")


# ─────────────────────────────────────────────────────────────────────────────
# 9. NATURAL LANGUAGE (needs a ByteFlow provider)
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("9. NATURAL LANGUAGE AUTOMATION (requires provider)")
print("=" * 60)

print("""
To use natural language automation, connect a ByteFlow provider:

    from byteflow_automator import Automator
    from byteflow.providers.ollama_provider import OllamaProvider

    provider = OllamaProvider(model="llama2")
    auto = Automator(provider=provider)

    # Now you can use plain English:
    auto.run("show me the git status of ~/myproject")
    auto.run("install requests and show pip list")
    auto.run("open vscode in ~/myproject")
    auto.run("create a python project called my-api in ~/projects")
    auto.run("run the build.sh script in ~/myapp")
    auto.run("what processes are using the most CPU?")

The ByteFlow brain plans which tasks to call.
The Automator executes them. ByteFlow stays lightweight.
""")

print("Done! All examples ran successfully.")
