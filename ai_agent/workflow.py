"""LangGraph workflow definition for Socket Recommendation AI Agent system."""

from typing import TypedDict, Dict, Any, List, Optional
from langgraph.graph import StateGraph, END

from models.request import SocketRecommendationRequest
from models.response import SocketRecommendationResponse

from agents.orchestrator import OrchestratorAgent
from agents.image_analysis_agent import ImageAnalysisAgent
from agents.geometry_agent import GeometryAgent
from agents.clinical_agent import ClinicalAgent
from agents.socket_agent import SocketAgent
from agents.safety_agent import SafetyAgent
from agents.decision_agent import DecisionAgent


class AgentState(TypedDict):
    """The state schema shared across all nodes in the workflow."""

    request: SocketRecommendationRequest
    image_analysis_results: Optional[Dict[str, Any]]
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
    image_analysis = ImageAnalysisAgent()
    geometry = GeometryAgent()
    clinical = ClinicalAgent()
    socket_agent = SocketAgent()
    safety = SafetyAgent()
    decision = DecisionAgent()

    # 2. Define the StateGraph with the schema
    workflow = StateGraph(AgentState)

    # Wrap orchestrator.run to dynamically route based on image_folder_path
    def run_orchestrator(state: AgentState) -> Dict[str, Any]:
        result = orchestrator.run(state)
        request = state.get("request")
        if request and getattr(request, "image_folder_path", None):
            result["next_step"] = "image_analysis_agent"
        else:
            result["next_step"] = "geometry_agent"
        return result

    # 3. Add nodes corresponding to agents
    workflow.add_node("orchestrator", run_orchestrator)
    workflow.add_node("image_analysis_agent", image_analysis.run)
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
            "image_analysis_agent": "image_analysis_agent",
            "geometry_agent": "geometry_agent",
            "clinical_agent": "clinical_agent",
            "socket_agent": "socket_agent",
            "safety_agent": "safety_agent",
            "decision_agent": "decision_agent",
        },
    )

    # Sequence of execution: Image Analysis -> Geometry -> Clinical -> Socket recommendation parameters -> Safety -> Decision Synthesis
    workflow.add_edge("image_analysis_agent", "geometry_agent")
    workflow.add_edge("geometry_agent", "clinical_agent")
    workflow.add_edge("clinical_agent", "socket_agent")
    workflow.add_edge("socket_agent", "safety_agent")
    workflow.add_edge("safety_agent", "decision_agent")
    workflow.add_edge("decision_agent", END)

    # Compile the graph
    return workflow.compile()


# Build a default graph instance
recommendation_graph = build_workflow()


def create_graph():
    """Builds and compiles the LangGraph StateGraph recommendation workflow."""
    return build_workflow()

