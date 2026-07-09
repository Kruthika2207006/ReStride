"""LangGraph workflow definition for Socket Recommendation AI Agent system."""

from typing import TypedDict, Dict, Any, List
from langgraph.graph import StateGraph, END

from models.request import SocketRecommendationRequest
from models.response import SocketRecommendationResponse

from agents.orchestrator import OrchestratorAgent
from agents.geometry_agent import GeometryAgent
from agents.clinical_agent import ClinicalAgent
from agents.socket_agent import SocketAgent
from agents.safety_agent import SafetyAgent
from agents.decision_agent import DecisionAgent


class AgentState(TypedDict):
    """The state schema shared across all nodes in the workflow."""

    request: SocketRecommendationRequest
    geometry_analysis_results: Dict[str, Any]
    clinical_analysis: Dict[str, Any]
    socket_recommendation: Dict[str, Any]
    safety_analysis: Dict[str, Any]
    final_response: SocketRecommendationResponse
    next_step: str
    routing_loop_count: int
    errors: List[str]


def build_workflow() -> StateGraph:
    """Builds and compiles the LangGraph StateGraph workflow.

    Returns:
        A compiled StateGraph executable.
    """
    # 1. Initialize our agents
    orchestrator = OrchestratorAgent()
    geometry = GeometryAgent()
    clinical = ClinicalAgent()
    socket_agent = SocketAgent()
    safety = SafetyAgent()
    decision = DecisionAgent()

    # 2. Define the StateGraph with the schema
    workflow = StateGraph(AgentState)

    # 3. Add nodes corresponding to agents
    workflow.add_node("orchestrator", orchestrator.run)
    workflow.add_node("geometry_agent", geometry.run)
    workflow.add_node("clinical_agent", clinical.run)
    workflow.add_node("socket_agent", socket_agent.run)
    workflow.add_node("safety_agent", safety.run)
    workflow.add_node("decision_agent", decision.run)

    # 4. Configure graph flow (edges)
    workflow.set_entry_point("orchestrator")

    # Orchestrator decides where to route next (conditional edge)
    workflow.add_conditional_edges(
        "orchestrator",
        orchestrator.route,
        {
            "geometry_agent": "geometry_agent",
            "clinical_agent": "clinical_agent",
            "socket_agent": "socket_agent",
            "safety_agent": "safety_agent",
            "decision_agent": "decision_agent",
        },
    )

    # Sequence of execution: Geometry -> Clinical -> Socket recommendation parameters -> Safety -> Decision Synthesis
    workflow.add_edge("geometry_agent", "clinical_agent")
    workflow.add_edge("clinical_agent", "socket_agent")
    workflow.add_edge("socket_agent", "safety_agent")
    workflow.add_edge("safety_agent", "decision_agent")
    workflow.add_edge("decision_agent", END)

    # Compile the graph
    return workflow.compile()


# Build a default graph instance
recommendation_graph = build_workflow()
