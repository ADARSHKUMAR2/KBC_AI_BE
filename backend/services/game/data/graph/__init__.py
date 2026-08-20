"""
graph/__init__.py
-----------------
Public API of the graph package.

External code only ever needs run_question_generation().
Everything else (nodes, state, graph builder) is internal.
"""

from backend.services.game.data.graph.question_graph import run_question_generation

__all__ = ["run_question_generation"]
