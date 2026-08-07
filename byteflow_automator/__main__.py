"""
ByteFlow Automator CLI
======================
Run automation tasks directly from the command line.

Usage:
    python -m byteflow_automator <task> [args...]
    python -m byteflow_automator list
    python -m byteflow_automator info <task>
    python -m byteflow_automator capabilities

Examples:
    python -m byteflow_automator git_status ~/myproject
    python -m byteflow_automator pip_install requests
    python -m byteflow_automator open_app vscode
    python -m byteflow_automator run_command "ls -la"
    python -m byteflow_automator system_info
    python -m byteflow_automator scaffold_python_project my-api ~/projects
"""

import sys
import json
from byteflow_automator import Automator


def main():
    auto = Automator()

    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    # Meta commands
    if cmd == "list":
        tasks = auto.list_tasks()
        print(f"\nAvailable tasks ({len(tasks)}):\n")
        for name in sorted(tasks):
            task = auto.registry.get(name)
            print(f"  {name:<30} {task.description}")
        print()
        return

    if cmd == "capabilities":
        print(auto.capabilities())
        return

    if cmd == "info" and args:
        print(auto.describe_task(args[0]))
        return

    # Run a task directly
    if cmd not in auto.registry:
        print(f"Error: unknown task '{cmd}'")
        print(f"Run `python -m byteflow_automator list` to see all tasks.")
        sys.exit(1)

    # Auto-cast args to int/bool where possible
    def coerce(v):
        if v.lower() == "true": return True
        if v.lower() == "false": return False
        try: return int(v)
        except ValueError: pass
        return v

    coerced_args = [coerce(a) for a in args]
    result = auto.run_task(cmd, *coerced_args)

    if isinstance(result, (dict, list)):
        print(json.dumps(result, indent=2, default=str))
    else:
        print(result)


if __name__ == "__main__":
    main()
