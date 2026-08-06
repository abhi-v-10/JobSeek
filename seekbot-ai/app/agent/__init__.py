"""
SeekBot agent runtime.

An objective-driven execution pipeline that replaces single-intent routing:

    User request
        ↓  planner.build_plan()        objectives, not keywords
        ↓  context.load_context()      required information (parallel)
        ↓  executor.execute_plan()     capabilities (parallel where independent)
        ↓  completion.verify()         one lightweight check
        ↓  composer.compose()          single concise response
        ↓  Final response

Public entry point:
    from app.agent import run_agent
"""

from app.agent.orchestrator import run_agent

__all__ = ["run_agent"]
