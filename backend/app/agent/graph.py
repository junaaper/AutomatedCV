"""The job-application agent:

extract_requirements -> retrieve_evidence -> score_fit -> draft_cover_letter
    -> human_review --approve/edit--> save_application -> END
                    --revise--> draft_cover_letter
                    --reject--> END
"""

from langgraph.graph import END, START, StateGraph

from app.agent import nodes
from app.agent.state import AgentContext, AgentState


def build_graph() -> StateGraph:
    g = StateGraph(AgentState, context_schema=AgentContext)
    g.add_node("extract_requirements", nodes.extract_requirements)
    g.add_node("retrieve_evidence", nodes.retrieve_evidence)
    g.add_node("score_fit", nodes.score_fit)
    g.add_node("draft_cover_letter", nodes.draft_cover_letter)
    g.add_node(
        "human_review",
        nodes.human_review,
        destinations=("save_application", "draft_cover_letter", END),
    )
    g.add_node("save_application", nodes.save_application)

    g.add_edge(START, "extract_requirements")
    g.add_edge("extract_requirements", "retrieve_evidence")
    g.add_edge("retrieve_evidence", "score_fit")
    g.add_edge("score_fit", "draft_cover_letter")
    g.add_edge("draft_cover_letter", "human_review")
    g.add_edge("save_application", END)
    return g
