import os


def read_code_file(path, max_chars=20000):
    """
    Read a source file's contents for the agent to discuss.
    Truncates very large files so prompts stay a reasonable size.
    """
    if not os.path.isfile(path):
        return f"[Error] File not found: {path}"

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except OSError as e:
        return f"[Error] Could not read {path}: {e}"

    if len(content) > max_chars:
        content = content[:max_chars] + "\n\n... [truncated] ..."

    return content


def explain_code(agent, path, question="Explain what this code does."):
    """
    Convenience helper: read a file and ask the agent about it via chat().
    Usage:
        from byteflow.codehelp import explain_code
        explain_code(agent, "myscript.py", "Find any bugs in this.")
    """
    code = read_code_file(path)
    if code.startswith("[Error]"):
        return code

    message = f"""I have a code file at `{path}`. Here is its content:

```
{code}
```

{question}
"""
    return agent.chat(message)
