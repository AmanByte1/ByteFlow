"""
Auto-discovery connector system for ByteFlow extensions.

Drop a folder into byteflow/extensions/ (or point at any folder on
disk, e.g. a sibling project like DataLab) and ByteFlow finds it,
loads it, and registers whatever tools it exposes onto an Agent -
without editing any ByteFlow code to wire it in by hand.

This builds directly on the existing Plugin base class (plugin.py) -
the only new thing here is DISCOVERY (finding and loading plugins
automatically from a folder convention), not how a plugin works once
loaded. A Plugin's setup(agent) does exactly what it always did.

## The convention

For a folder to be discovered as an extension, it must contain a file
named `byteflow_plugin.py` with a module-level function:

    def get_plugin():
        return SomePlugin(...)   # a Plugin subclass instance

That's the entire contract. get_plugin() is a function (not a
module-level instance) deliberately - it defers construction until
the extension is actually being loaded, so an extension with heavy
optional dependencies (pandas, tensorflow, ...) only pays that import
cost when someone actually loads it, not just by existing on disk.

## Failure handling

A broken or dependency-missing extension must never take down the
whole agent, or prevent other extensions from loading. Every extension
is loaded in isolation inside a try/except; failures are collected
into the returned report rather than raised. Check the "status" field
of each report rather than assuming a call to load_all_extensions()
succeeding means every extension loaded.
"""

import os
import sys
import importlib.util


PLUGIN_ENTRY_FILENAME = "byteflow_plugin.py"


def default_extensions_dir():
    """byteflow/extensions/ next to this file - the built-in, always-
    scanned location. Extensions can also be loaded from anywhere else
    on disk via load_extension()/load_all_extensions()'s explicit path
    argument (e.g. a sibling project like DataLab that isn't inside
    the ByteFlow repo at all)."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "extensions")


def discover_extension_folders(extensions_dir):
    """
    Return the list of subdirectories of `extensions_dir` that contain
    a byteflow_plugin.py entry point. Pure discovery - doesn't import
    or load anything, so callers can inspect what WOULD be loaded
    before actually loading it (see `byteflow extensions list`).
    """
    if not os.path.isdir(extensions_dir):
        return []

    found = []
    for entry in sorted(os.listdir(extensions_dir)):
        folder = os.path.join(extensions_dir, entry)
        entry_point = os.path.join(folder, PLUGIN_ENTRY_FILENAME)
        if os.path.isdir(folder) and os.path.isfile(entry_point):
            found.append(folder)
    return found


def _load_entry_module(entry_point, module_name):
    """Import byteflow_plugin.py from an arbitrary folder as a
    uniquely-named module - works whether or not the extension is
    pip-installed or permanently on sys.path."""
    spec = importlib.util.spec_from_file_location(module_name, entry_point)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_extension(folder, agent):
    """
    Load a single extension folder onto `agent`. Returns a report dict:
        {"name": ..., "path": ..., "status": "loaded" | "failed", "error": str or None}

    Never raises. A missing entry point, a missing get_plugin()
    function, a missing dependency inside the extension, or a bug in
    its setup() all come back as {"status": "failed", "error": "..."}
    rather than propagating - see the module docstring for why.
    """
    folder = os.path.abspath(folder)
    folder_name = os.path.basename(os.path.normpath(folder))
    entry_point = os.path.join(folder, PLUGIN_ENTRY_FILENAME)

    if not os.path.isfile(entry_point):
        return {
            "name": folder_name, "path": folder, "status": "failed",
            "error": f"No {PLUGIN_ENTRY_FILENAME} found in {folder}",
        }

    # Extensions typically live outside the byteflow package (a
    # sibling project like DataLab) and import their own top-level
    # package (e.g. `from datalab import ...`, where `datalab/` is a
    # subfolder of the extension folder itself) from inside
    # byteflow_plugin.py or the tool functions it registers - add the
    # extension folder ITSELF to sys.path so that import resolves.
    # Left on sys.path for the rest of the process (not removed
    # afterward) since a lazily-imported tool function may need it
    # again long after loading finishes.
    if folder not in sys.path:
        sys.path.insert(0, folder)

    try:
        module_name = f"_byteflow_extension_{folder_name}"
        module = _load_entry_module(entry_point, module_name)

        if not hasattr(module, "get_plugin"):
            return {
                "name": folder_name, "path": folder, "status": "failed",
                "error": f"{PLUGIN_ENTRY_FILENAME} must define a get_plugin() function",
            }

        plugin = module.get_plugin()
        agent.load_plugin(plugin)
        return {"name": folder_name, "path": folder, "status": "loaded", "error": None}

    except Exception as e:
        return {"name": folder_name, "path": folder, "status": "failed", "error": str(e)}


def load_all_extensions(agent, extensions_dir=None, extra_paths=None):
    """
    Discover and load every extension onto `agent`:
      - every subfolder of `extensions_dir` (default: byteflow/extensions/)
        that has a byteflow_plugin.py, PLUS
      - every folder explicitly listed in `extra_paths` (for
        extensions that live entirely outside the ByteFlow repo, like
        a sibling DataLab/ project - point at it directly rather than
        needing to be copied/symlinked into byteflow/extensions/).

    Always completes, even if some extensions fail - returns the list
    of per-extension reports (see load_extension()); check "status" on
    each rather than assuming success.
    """
    extensions_dir = extensions_dir or default_extensions_dir()
    folders = discover_extension_folders(extensions_dir)
    folders += [os.path.abspath(p) for p in (extra_paths or [])]

    return [load_extension(folder, agent) for folder in folders]
