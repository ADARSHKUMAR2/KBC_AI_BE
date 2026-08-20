"""
graph/question_graph.py
------------------------
Phase 5 LangGraph pipeline assembler and public entry point.

This file:
1. Imports all 4 node functions from graph/nodes/
2. Defines the conditional routing logic (retry or save?)
3. Builds and compiles the StateGraph
4. Exposes run_question_generation() — the only function callers need

Pipeline Flow:
    START
      │
      ▼
  research_node     ← fetches real-time news (no LLM)
      │
      ▼
  writer_node       ← LLM drafts a trivia question (DraftQuestionSchema)
      │
      ▼
  validator_node    ← LLM judges the draft (ValidationResultSchema)
      │
      ├── is_valid=True OR retry_count >= MAX_RETRIES
      │         └──────────────────► saver_node → END
      │
      └── is_valid=False AND retry_count < MAX_RETRIES
                └──────────────────► writer_node (retry with next story)

Callers:
    - POST /game/generate-question  (on-demand via game_routes.py)
    - APScheduler cron job          (daily at midnight via game/main.py)
"""

from langgraph.graph import StateGraph, END

from backend.services.game.data.graph.state import QuestionGenState
from backend.services.game.data.graph.nodes import (
    research_node,
    writer_node,
    validator_node,
    saver_node
)


# ── Constants ────────────────────────────────────────────────────────────────
MAX_RETRIES = 2   # Maximum Writer retries before saving whatever we have


# ═══════════════════════════════════════════════════════════════════════════
# CONDITIONAL EDGE — Routing logic after validator_node
# ═══════════════════════════════════════════════════════════════════════════

def should_retry_or_save(state: QuestionGenState) -> str:
    """
    Routing function called after validator_node completes.

    Reads is_valid and retry_count from state to decide next node.

    Returns:
        "writer_node" → question rejected, retries remaining → try again
        "saver_node"  → question approved OR max retries hit → save and finish
    """
    is_valid    = state.get("is_valid", False)
    retry_count = state.get("retry_count", 0)

    if is_valid:
        print(f"✅ [Router] Approved on retry #{retry_count} → routing to saver_node")
        return "saver_node"

    if retry_count < MAX_RETRIES:
        print(f"🔁 [Router] Rejected (retry #{retry_count}/{MAX_RETRIES}) → routing to writer_node")
        return "writer_node"

    # Max retries exhausted — save the best we have
    print(f"⚠️  [Router] Max retries ({MAX_RETRIES}) reached → routing to saver_node (best-effort)")
    return "saver_node"


# ═══════════════════════════════════════════════════════════════════════════
# GRAPH ASSEMBLY
# ═══════════════════════════════════════════════════════════════════════════

def _build_graph() -> StateGraph:
    """
    Assembles and compiles the LangGraph state machine.
    Called once at module import — not on every pipeline run.
    """
    graph = StateGraph(QuestionGenState)

    # ── Register nodes ───────────────────────────────────────────────────
    graph.add_node("research_node",  research_node)
    graph.add_node("writer_node",    writer_node)
    graph.add_node("validator_node", validator_node)
    graph.add_node("saver_node",     saver_node)

    # ── Define edges ─────────────────────────────────────────────────────
    graph.set_entry_point("research_node")

    graph.add_edge("research_node",  "writer_node")
    graph.add_edge("writer_node",    "validator_node")

    # Conditional edge: validator → (writer retry | saver)
    graph.add_conditional_edges(
        source="validator_node",
        path=should_retry_or_save,
        path_map={
            "writer_node": "writer_node",
            "saver_node":  "saver_node",
        }
    )

    graph.add_edge("saver_node", END)

    return graph.compile()


# ── Compile graph once at module load ────────────────────────────────────────
_compiled_graph = _build_graph()


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

async def run_question_generation() -> dict:
    """
    Run the full Phase 5 question generation pipeline.

    This is the ONLY function external code should call.
    Imported by:
        - game_routes.py  (POST /game/generate-question)
        - game/main.py    (APScheduler daily cron)

    Returns:
        {
            "success":       bool,
            "question_id":   str | None,   # MongoDB _id of saved question
            "question_text": str | None,   # For confirmation logging/response
            "error":         str | None    # Human-readable error if failed
        }
    """
    print("\n" + "=" * 60)
    print("🚀 Phase 5 Question Generation Pipeline — START")
    print("=" * 60)

    # All fields must be present in initial state (TypedDict requires it)
    initial_state: QuestionGenState = {
        "news_stories":       [],
        "chosen_story":       None,
        "draft_question":     None,
        "is_valid":           False,
        "validation_reason":  "",
        "retry_count":        0,
        "final_question":     None,
        "saved_question_id":  None,
        "error":              None,
    }

    try:
        final_state = await _compiled_graph.ainvoke(initial_state)

        if final_state.get("saved_question_id"):
            q_text = (final_state.get("final_question") or {}).get("question_text", "")
            print(f"\n🎉 Pipeline SUCCESS — Question ID: {final_state['saved_question_id']}")
            print("=" * 60 + "\n")
            return {
                "success":       True,
                "question_id":   final_state["saved_question_id"],
                "question_text": q_text,
                "error":         None
            }
        else:
            err = final_state.get("error") or "Unknown failure — question was not saved."
            print(f"\n❌ Pipeline FAILED: {err}")
            print("=" * 60 + "\n")
            return {
                "success":       False,
                "question_id":   None,
                "question_text": None,
                "error":         err
            }

    except Exception as e:
        print(f"\n💥 Pipeline CRASHED: {e}")
        print("=" * 60 + "\n")
        return {
            "success":       False,
            "question_id":   None,
            "question_text": None,
            "error":         str(e)
        }
