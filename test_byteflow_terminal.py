"""
Terminal smoke test for ByteFlow - checks the major fixes made so far
all actually work, without needing a real LLM/Ollama running (uses a
fake provider standing in for the model, so this tests ByteFlow's own
logic, not the quality of whatever local model you have installed).

Usage:
    cd ByteFlow
    python test_byteflow_terminal.py

Each test prints PASS or FAIL with a short reason. Exits with code 1
if anything fails, 0 if everything passes - safe to use in a script.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from byteflow.agent import Agent
from byteflow.tools import Tool

passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  PASS - {name}")
        passed += 1
    else:
        print(f"  FAIL - {name}" + (f" ({detail})" if detail else ""))
        failed += 1


print("=" * 70)
print("TEST GROUP 1: Open/launch request extraction")
print("=" * 70)
agent = Agent(provider=None, memory_path=False)
check(
    '"open file name aman" extracts to just "aman"',
    agent._extract_open_target("open file name aman") == "aman",
)
check(
    r'"open file D:\Sem3" extracts to a real valid path',
    agent._extract_open_target(r"open file D:\Sem3") == r"D:\Sem3",
)

print()
print("=" * 70)
print("TEST GROUP 2: Code generation safety (never execute non-code)")
print("=" * 70)


class TruncatedProvider:
    def generate(self, prompt):
        if "durable fact" in prompt:
            return "none"
        return "To run this code, you will need to install Flask. You can do this with pip:"


agent = Agent(provider=TruncatedProvider(), memory_path=False)
result = agent.code("write a code for simple website", execute=True)
check(
    "invalid/incomplete code is not executed as a raw crash",
    result["result"].success is False and "No valid Python code was generated" in result["result"].stderr,
    detail=result["result"].stderr[:80],
)


class NormalCodeProvider:
    def generate(self, prompt):
        if "durable fact" in prompt:
            return "none"
        return "```python\nprint(2 + 2)\n```"


agent = Agent(provider=NormalCodeProvider(), memory_path=False)
result = agent.code("add two numbers", execute=True)
check(
    "genuinely valid code still executes normally",
    result["result"].success is True and "4" in result["result"].stdout,
)

print()
print("=" * 70)
print("TEST GROUP 3: Search query broadening")
print("=" * 70)
check(
    '"today top 10 news" broadens to "news"',
    Agent._broaden_search_query("today top 10 news") == "news",
)

print()
print("=" * 70)
print("TEST GROUP 4: Tool-call hallucination prevention (arity checking)")
print("=" * 70)
agent = Agent(provider=None, memory_path=False)
multiply_tool = Tool("multiply", lambda a, b: a * b, "multiplies two numbers")
check(
    "wrong argument count is rejected (the real observed multiply/car_data_clean_report bug)",
    agent._args_fit_tool_signature(multiply_tool, ["some_other_tool_name"]) is False,
)
check(
    "correct argument count is accepted",
    agent._args_fit_tool_signature(multiply_tool, [3, 4]) is True,
)

print()
print("=" * 70)
print("TEST GROUP 5: Document-focus framing only when actually relevant")
print("=" * 70)


class CapturingProvider:
    def __init__(self):
        self.last_prompt = ""

    def generate(self, prompt):
        self.last_prompt = prompt
        return "none" if "durable fact" in prompt else "answer"


provider = CapturingProvider()
agent = Agent(provider=provider, memory_path=False)
agent.vector_store.add_document("Course syllabus: Discrete Mathematics has 4 credits.", source="syllabus.pdf")
agent.active_document_source = "syllabus.pdf"
agent.chat("give me the current rate of each car with future price prediction")
check(
    "unrelated message does NOT trigger 'currently focused on document' framing",
    "currently focused on the document" not in provider.last_prompt,
)

print()
print("=" * 70)
print("TEST GROUP 6: Memory poisoning prevention")
print("=" * 70)


class HallucinatingExtractionProvider:
    def generate(self, prompt):
        return "The predict_price function is missing year and mileage_km arguments"


agent = Agent(provider=HallucinatingExtractionProvider(), memory_path=False)
result = agent.learn_from_exchange(
    "predict car price 2028 which runs 10000km",
    "there was an issue with the predict_price() tool",
)
check(
    "hallucinated tool-error claim is never saved as a permanent fact",
    result is None and agent.profile.all_facts() == [],
)

agent = Agent(provider=None, memory_path=False)
agent.add_memory("user", "predict car price 2028 which runs 10000km")
agent.add_memory(
    "assistant",
    "As we discussed earlier, there was an issue with the predict_price() "
    "function missing two required positional arguments: 'year' and 'mileage_km'.",
)
for i in range(10):
    agent.add_memory("user", f"unrelated filler {i}")
    agent.add_memory("assistant", f"unrelated filler reply {i}")
context, _ = agent.recalled_context("predict car price 2030 with 5000km")
check(
    "old hallucinated assistant reply is not resurfaced by semantic search",
    "predict_price() function missing" not in context,
)

print()
print("=" * 70)
print("TEST GROUP 7: Fact extraction preamble stripping (deduplication fix)")
print("=" * 70)
variants = [
    "The durable fact worth remembering is:\nUser's name is Aman",
    "The durable fact is: User's name is Aman",
    "User's name is Aman",
]
stripped = [Agent._strip_extraction_preamble(v) for v in variants]
check(
    "all real observed junk variants normalize to the same clean fact",
    len(set(stripped)) == 1 and stripped[0] == "User's name is Aman",
    detail=str(stripped),
)

print()
print("=" * 70)
print("TEST GROUP 8: Document-loaded no longer hijacks tool requests")
print("=" * 70)
agent = Agent(provider=None, memory_path=False)
agent.vector_store.add_document("syllabus content here", source="syllabus.pdf")
agent.register_tool(Tool(
    "predict_car_price", lambda year, km: "predicted price",
    "predicts the selling price for a NEW hypothetical car given its year and km_driven",
))
check(
    '"predict car price 2028 which runs 10000km" reaches the tool planner even with a document loaded',
    agent._looks_like_document_request("predict car price 2028 which runs 10000km") is False,
)

print()
print("=" * 70)
print(f"RESULTS: {passed} passed, {failed} failed")
print("=" * 70)

if failed > 0:
    sys.exit(1)
