"""Coordinator agent: decomposes research topics and delegates to subagents.

The coordinator's tool set has ONE tool: Task. Per Task 1.3, that's the
mechanism for spawning subagents. The Task tool's implementation reads
the requested agent_name, looks it up in the subagent registry, and
runs the subagent with the provided prompt.

The coordinator's system prompt (in src/prompts.py / inline below)
embodies the architectural rules from Tasks 1.2 and 1.6:
- Decompose broadly enough to cover the full topic
- Delegate based on subagent specialization
- Use parallel emission when subagents can investigate independently
- Aggregate findings preserving provenance
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from .agent_loop import AgentRun, run_agent_loop
from .subagents import SUBAGENT_REGISTRY, SubagentResult


COORDINATOR_SYSTEM_PROMPT = """You are a research coordinator. Your job \
is to investigate a research topic by delegating to specialist subagents, \
then aggregating their findings.

## Available subagents

You have two subagents you can invoke via the `Task` tool:

1. **web_research** — searches the web for news articles, industry \
reports, and general-audience sources. Good for current events, surveys, \
market commentary.

2. **document_analysis** — analyzes academic papers, in-depth studies, \
and longer-form reports. Good for primary research, economic analysis, \
detailed surveys.

## How to decompose a research topic

When given a topic, identify the FULL SET of domains, sub-topics, or \
perspectives that the topic might span. Do NOT narrow prematurely. For \
example, "the impact of AI on creative industries" spans visual arts, \
music, writing, film, theatre, photography, graphic design — at minimum. \
A decomposition that only covers visual arts is incomplete.

For each domain you identify, decide whether to delegate to web_research, \
document_analysis, or both. Use both when you want a mix of current news \
and deeper studies.

## How to delegate

Emit `Task` tool calls to invoke subagents. When you have multiple \
INDEPENDENT subtasks (different domains, different source types), emit \
the Task calls in PARALLEL — multiple tool_use blocks in one response. \
This is faster than serial delegation.

When you delegate, include in each Task's prompt:
- A focused query (1-2 sentences)
- The relevant domain hint (e.g., `domain: music`)
- Any quality criteria specific to the subtopic

The subagent does not see this conversation. It only sees the prompt \
you give it. Pack what it needs.

## What to do after subagent results return

When all subagent results are back, review them:
- Are all domains you identified covered?
- Are there subdomains the findings reveal that you should investigate?
- Are there conflicts or contradictions between sources that need a \
follow-up query?

If coverage is incomplete, delegate additional Task calls. If coverage \
is adequate, produce a brief end_turn response indicating you're ready \
to synthesize. DO NOT attempt to synthesize the final report yourself — \
that's a separate stage.

## Output

When investigation is complete, respond with `end_turn` and a brief \
message stating: number of domains investigated, total findings collected, \
and readiness to proceed to synthesis."""


# --- The Task tool ---

TASK_TOOL_SCHEMA = {
    "name": "Task",
    "description": (
        "Spawn a specialist subagent to investigate a focused subtopic. "
        "The subagent runs independently with isolated context and "
        "returns structured findings."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {
                "type": "string",
                "enum": list(SUBAGENT_REGISTRY.keys()),
                "description": (
                    "Which specialist to invoke. Use 'web_research' for "
                    "current articles and industry reports; "
                    "'document_analysis' for papers and in-depth studies."
                ),
            },
            "prompt": {
                "type": "string",
                "description": (
                    "The full prompt for the subagent. Must include a "
                    "focused query and any domain hints. The subagent "
                    "does not see the coordinator's conversation; pack "
                    "all needed context here."
                ),
            },
        },
        "required": ["agent_name", "prompt"],
    },
}


def _task_tool_implementation(tool_input: dict) -> dict:
    """Dispatch a Task tool call to the named subagent.

    Per Task 1.3, this is the spawn mechanism. The subagent runs in
    isolated context (it only sees the prompt the coordinator passed).
    The result is returned as a dict that the coordinator's loop will
    wrap in a tool_result block.
    """
    agent_name = tool_input.get("agent_name")
    prompt = tool_input.get("prompt", "")

    if agent_name not in SUBAGENT_REGISTRY:
        return {
            "isError": True,
            "errorCategory": "validation",
            "isRetryable": False,
            "message": f"Unknown subagent: {agent_name}",
            "available_agents": list(SUBAGENT_REGISTRY.keys()),
        }

    if not prompt:
        return {
            "isError": True,
            "errorCategory": "validation",
            "isRetryable": False,
            "message": "Task tool requires a non-empty prompt.",
        }

    subagent = SUBAGENT_REGISTRY[agent_name]
    result: SubagentResult = subagent.runner(prompt)

    if result.is_error:
        return {
            "isError": True,
            "errorCategory": result.error_category or "transient",
            "isRetryable": result.error_category == "transient",
            "subagent": agent_name,
            "attempted_prompt": prompt[:200],
            "coverage_note": result.coverage_note,  # contains alternatives
            "error_detail": result.error_detail,
        }

    # Pack the subagent's result into the tool_result that the
    # coordinator's loop will receive.
    return {
        "subagent": agent_name,
        "findings_count": len(result.findings),
        "findings": result.findings,
        "coverage_note": result.coverage_note,
    }


# --- Aggregated research result ---

@dataclass
class ResearchSession:
    """All the state and outputs of one coordinator-led investigation."""
    topic: str
    coordinator_run: AgentRun | None = None
    subagent_invocations: list[dict] = field(default_factory=list)
    all_findings: list[dict] = field(default_factory=list)

    def add_invocation(self, agent_name: str, prompt: str, result: dict):
        self.subagent_invocations.append({
            "agent_name": agent_name,
            "prompt": prompt,
            "result": result,
        })
        if not result.get("isError"):
            self.all_findings.extend(result.get("findings", []))


# --- The coordinator's run function ---

def run_coordinator(topic: str) -> ResearchSession:
    """Run the coordinator on a research topic.

    Returns the ResearchSession with all subagent invocations and
    aggregated findings recorded.
    """
    session = ResearchSession(topic=topic)

    # The Task tool's implementation needs to write into the session
    # for our observability. We close over session via a wrapper.
    def task_impl_with_session(tool_input: dict) -> dict:
        result = _task_tool_implementation(tool_input)
        session.add_invocation(
            agent_name=tool_input.get("agent_name", ""),
            prompt=tool_input.get("prompt", ""),
            result=result,
        )
        return result

    tool_implementations = {"Task": task_impl_with_session}
    tool_schemas = [TASK_TOOL_SCHEMA]

    run, _history = run_agent_loop(
        user_message=f"Research this topic and produce a findings report: {topic}",
        system_prompt=COORDINATOR_SYSTEM_PROMPT,
        tool_schemas=tool_schemas,
        tool_implementations=tool_implementations,
    )

    session.coordinator_run = run
    return session