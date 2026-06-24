from langgraph.graph import StateGraph, END
from state import EpistemicState
from core.planner import planner
from core.evidence import evidence_collection
from core.critic import claim_extraction, claim_critic, coverage_critic
from core.synthesis import gap_detection, hypothesis_generation, validator, writer

# Initialize the state graph configuration with our structured schema
workflow = StateGraph(EpistemicState)

# 1. Register all analytical processing nodes
workflow.add_node("planner", planner)
workflow.add_node("evidence_collection", evidence_collection)
workflow.add_node("claim_extraction", claim_extraction)
workflow.add_node("claim_critic", claim_critic)
workflow.add_node("gap_detection", gap_detection)
workflow.add_node("hypothesis_generation", hypothesis_generation)
workflow.add_node("validator", validator)
workflow.add_node("writer", writer)

# 2. Wire up the strict step-by-step entry pipeline
workflow.set_entry_point("planner")
workflow.add_edge("planner", "evidence_collection")
workflow.add_edge("evidence_collection", "claim_extraction")
workflow.add_edge("claim_extraction", "claim_critic")

# 3. Inject the conditional loop-back gatekeeper
# The coverage_critic dictates whether to iterate or move to synthesis
workflow.add_conditional_edges(
    "claim_critic",
    coverage_critic,
    {
        "research_more": "evidence_collection",
        "proceed": "gap_detection"
    }
)

# 4. Wire up the post-synthesis verification and compilation track
workflow.add_edge("gap_detection", "hypothesis_generation")
workflow.add_edge("hypothesis_generation", "validator")
workflow.add_edge("validator", "writer")
workflow.add_edge("writer", END)

# Compile into an executable application graph
app_graph = workflow.compile()