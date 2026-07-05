# ByteFlow Extensions

Drop a folder in here (or point at one anywhere on disk - see below)
and ByteFlow finds it, loads it, and registers whatever tools it
provides onto the Agent. No changes to ByteFlow's own code required.

## Making a folder into an extension

Add a file named `byteflow_plugin.py` to your folder with a
module-level `get_plugin()` function that returns a `Plugin` instance
(the same `Plugin` base class ByteFlow has always had - see
`byteflow/plugin.py`):

```python
# my_extension/byteflow_plugin.py
from byteflow.plugin import Plugin
from byteflow.tools import Tool

class MyExtensionPlugin(Plugin):
    def setup(self, agent):
        agent.register_tool(Tool("my_tool", my_tool_function, "does something useful"))

def get_plugin():
    return MyExtensionPlugin("my_extension")
```

That's the entire contract. `get_plugin()` is a function (not a
ready-made instance) on purpose: construction - and any heavy imports
your extension needs (pandas, tensorflow, ...) - only happens when the
extension is actually loaded, not just by existing in this folder.

## Loading extensions

Extensions in this folder are auto-discovered. A project that lives
somewhere else entirely (e.g. a sibling `DataLab/` project, not copied
into ByteFlow's repo) can still be loaded by pointing at it directly:

```python
from byteflow.extension_loader import load_all_extensions

reports = load_all_extensions(agent, extra_paths=["/path/to/DataLab"])
for r in reports:
    print(r["name"], r["status"], r["error"])
```

Or from the CLI:

```
byteflow extensions list                     # see what would load, without loading it
byteflow run "..." --extension-path /path/to/DataLab
```

## Failure handling

A broken extension, or one whose dependencies aren't installed, is
reported (`status: "failed"`, with an `error` message) rather than
crashing ByteFlow or blocking other extensions from loading. Always
check the status of each report rather than assuming a call
succeeded.

## Example

See `extensions/example_hello/` for a minimal, fully working extension
with no external dependencies - a good starting point to copy.
