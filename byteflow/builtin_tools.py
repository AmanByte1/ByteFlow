"""
Small set of built-in tools the CLI registers by default, so basic
requests (like arithmetic) are actually computed by Python rather than
improvised by the LLM. Anyone using the Agent class directly can ignore
this and register their own tools instead.
"""

from .tools import Tool


def _to_number(value):
    """Convert a string/number arg to int or float."""
    if isinstance(value, (int, float)):
        return value
    try:
        return int(value)
    except (ValueError, TypeError):
        return float(value)


def _add(a, b):
    return _to_number(a) + _to_number(b)


def _subtract(a, b):
    return _to_number(a) - _to_number(b)


def _multiply(a, b):
    return _to_number(a) * _to_number(b)


def _divide(a, b):
    a, b = _to_number(a), _to_number(b)
    if b == 0:
        return "Error: division by zero"
    return a / b


def _web_search_raw(query, max_results=4):
    """
    Search the web (DuckDuckGo, no API key) and return raw formatted
    results - titles/snippets/URLs, NOT summarized by an LLM. Used only
    when no agent is available to do real summarization (see
    get_builtin_tools()'s agent parameter) - prefer the agent-bound
    version whenever possible, since raw search text dumped as a final
    answer reads poorly and doesn't synthesize anything.
    """
    from .web_search import search_formatted
    from .agent import Agent
    query = Agent._clean_search_query(query)
    return search_formatted(query, max_results=int(_to_number(max_results)))


def _make_web_search_tool(agent):
    """
    Build a web_search tool bound to `agent`, so it actually summarizes
    results into a real answer via agent.chat_with_search() - the same
    hard guarantee against fabricated results applies here (if search
    fails or finds nothing, the LLM is never called, an honest message
    is returned directly - see Agent.chat_with_search).

    Without this, web_search returned raw, unsummarized search text
    (titles/snippets/URLs) as the "answer" whenever the tool-planner
    picked it directly rather than routing through chat_with_search's
    auto-detection - a real observed bug ("top 10 ai news today"
    returned a raw Python list of search result text instead of an
    actual answer).
    """
    def _web_search_bound(query, max_results=4):
        return agent.chat_with_search(query, max_results=int(_to_number(max_results)))
    return _web_search_bound


def get_builtin_tools(agent=None):
    """
    Return the list of built-in Tool instances.

    Pass `agent` (the Agent these tools will be registered on) to get a
    web_search tool that properly summarizes results through the LLM,
    with the same anti-fabrication guarantee as auto-detected search.
    Without an agent, web_search falls back to returning raw formatted
    search text - still functional, just not summarized.
    """
    web_search_fn = _make_web_search_tool(agent) if agent is not None else _web_search_raw

    return [
        Tool("add", _add, "adds two numbers"),
        Tool("subtract", _subtract, "subtracts the second number from the first"),
        Tool("multiply", _multiply, "multiplies two numbers"),
        Tool("divide", _divide, "divides the first number by the second"),
        Tool("web_search", web_search_fn, "searches the web for current information and gives a summarized answer"),
    ]


def register_builtin_tools(agent):
    """Register all built-in tools onto the given agent."""
    for tool in get_builtin_tools(agent=agent):
        agent.register_tool(tool)
