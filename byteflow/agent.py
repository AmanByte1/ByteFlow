import json
import re
from .memory import Memory


class Agent:
    def __init__(self, provider=None):
        self.provider = provider
        self.tools = {}        # name -> Tool object
        self.plugins = []
        self.memory = Memory()

    # -----------------------------
    # TOOL SYSTEM
    # -----------------------------
    def register_tool(self, tool):
        self.tools[tool.name] = tool

    def use_tool(self, name, *args):
        return self.tools[name].run(*args)

    # -----------------------------
    # PLUGINS
    # -----------------------------
    def load_plugin(self, plugin):
        plugin.setup(self)
        self.plugins.append(plugin)

    # -----------------------------
    # MEMORY HELPERS
    # -----------------------------
    def add_memory(self, role, content):
        self.memory.add(role, content)

    # -----------------------------
    # SAFE ARG HANDLING
    # -----------------------------
    def safe_args(self, args):
        if not isinstance(args, list):
            return []

        return [
            a if isinstance(a, (int, float, str)) else str(a)
            for a in args
        ]

    # -----------------------------
    # JSON PARSER (ROBUST)
    # -----------------------------
    def extract_json(self, text):
        try:
            return json.loads(text)
        except:
            pass

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                return None

        return None

    # -----------------------------
    # PLANNER (MULTI STEP)
    # -----------------------------
    def plan(self, goal):
        if not self.provider:
            return None

        prompt = f"""
You are a planning system.

Break the task into steps using available tools.

Available tools:
{list(self.tools.keys())}

Goal:
{goal}

Return ONLY JSON list:
[
  {{"step": "tool_name", "args": [arg1, arg2]}},
  {{"step": "tool_name", "args": [arg1, arg2]}}
]
"""

        response = self.provider.generate(prompt)
        return self.extract_json(response)

    # -----------------------------
    # SINGLE STEP FALLBACK
    # -----------------------------
    def _single_step(self, prompt):
        tool_prompt = f"""
You are a STRICT tool selection engine.

Available tools:
{list(self.tools.keys())}

User request:
{prompt}

Return ONLY JSON:
{{
  "tool": "tool_name",
  "args": [arg1, arg2]
}}
"""

        response = self.provider.generate(tool_prompt)
        data = self.extract_json(response)

        if not data:
            return response

        tool_name = data.get("tool")

        if tool_name and tool_name in self.tools:
            args = self.safe_args(data.get("args", []))
            return self.tools[tool_name].run(*args)

        return data.get("answer", response)

    # -----------------------------
    # MAIN RUN LOOP (AUTONOMOUS)
    # -----------------------------
    def run(self, prompt):
        if not self.provider:
            return prompt

        # STEP 1: PLAN
        plan = self.plan(prompt)

        # fallback if planning fails
        if not plan:
            return self._single_step(prompt)

        results = []

        # STEP 2: EXECUTE PLAN
        for step in plan:
            tool_name = step.get("step")
            args = self.safe_args(step.get("args", []))

            if tool_name in self.tools:
                try:
                    result = self.tools[tool_name].run(*args)
                    results.append(result)

                    # store memory
                    self.add_memory("tool", f"{tool_name} -> {result}")

                except Exception as e:
                    results.append(f"[Tool Error]: {str(e)}")

            else:
                results.append(f"Tool not found: {tool_name}")

        # STEP 3: RETURN RESULT
        return results