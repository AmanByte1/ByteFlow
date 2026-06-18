import json
import re
class Agent:
    def __init__(self, provider=None):
        self.provider = provider
        self.tools = {}
        self.plugins = []
    
    def safe_args(self, args):
        if not isinstance(args, list):
            return []
    
        return [
         a if isinstance(a, (int, float, str)) else str(a)
         for a in args
     ]

    def extract_json(self,text):
        try:
            # Try direct JSON first
            return json.loads(text)
        except:
            pass
    
        # Try to extract JSON block from text
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                return None
    
        return None
    
    
     

    def register_tool(self, name, func):
        self.tools[name] = func

    def use_tool(self, name, *args):
        return self.tools[name](*args)

    def load_plugin(self, plugin):
        plugin.setup(self)
        self.plugins.append(plugin)

    def run(self, prompt):
        if not self.provider:
            return prompt
    
        tool_prompt = f"""
    You are a STRICT tool selection engine.

RULES:
- You MUST return ONLY valid JSON
- No extra text allowed
- No explanation
- No markdown

Available tools:
{list(self.tools.keys())}

TOOLS FORMAT:
Each tool takes EXACT arguments.

User request:
{prompt}

OUTPUT FORMAT:

If tool is needed:
{{
  "tool": "tool_name",
  "args": [arg1, arg2]
}}

If no tool needed:
{{
  "tool": null,
  "answer": "final answer"
}}
    """
    
        response = self.provider.generate(tool_prompt)
    
        data = self.extract_json(response)
    
        if not data:
            return f"[Parse Error] AI response: {response}"
    
        # TOOL EXECUTION
        if data.get("tool"):
            tool_name = data["tool"]
            args = self.safe_args(data.get("args", []))
    
            if tool_name in self.tools:
                result = self.tools[tool_name](*args)
                return f"Result: {result}"
    
            return f"Tool not found: {tool_name}"
    
        return data.get("answer", "No response")