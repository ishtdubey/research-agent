import os
from langchain_community.tools.tavily_search import TavilySearchResults
from state import EpistemicState, EvidenceItem
from utils.llm import get_llm

def evidence_collection(state: EpistemicState) -> dict:
    """
    Node: Gathers raw data items against the generated research plan targets.
    Enforces strict isolation between source collection and claim synthesis.
    """
    plan_queries = state.get("plan", [])
    if not plan_queries:
        # Fallback to initial user query if plan extraction was empty
        plan_queries = [state["query"]]
        
    search_tool = TavilySearchResults(max_results=3)
    collected_items = list(state.get("evidence", []))
    
    # Track existing source counts to prevent ID collisions on multi-iteration loops
    start_index = len(collected_items) + 1
    
    # Process queries sequentially
    for query in plan_queries:
        try:
            search_results = search_tool.invoke({"query": query})
            for idx, res in enumerate(search_results):
                source_id = f"src_{start_index:03d}"
                
                # Fast semantic check for domain taxonomy
                domain_type = "mixed"
                lower_q = query.lower()
                if any(x in lower_q for x in ["philosophy", "ethics", "political theory", "interpret"]):
                    domain_type = "interpretive"
                elif any(x in lower_q for x in ["quantum", "physics", "rna", "dataset", "benchmarks"]):
                    domain_type = "empirical"
                
                item: EvidenceItem = {
                    "source_id": source_id,
                    "title": res.get("title", f"Web Source Reference {source_id}"),
                    "url": res.get("url", "Unknown URL Source"),
                    "content": res.get("content", ""),
                    "domain": domain_type
                }
                collected_items.append(item)
                start_index += 1
        except Exception:
            # Silently pass or log to ensure network drops don't explode the whole state pipeline
            continue

    # Increment loop counter to provide safety bounds for the coverage critic
    current_iterations = state.get("research_iterations", 0) + 1

    return {
        "evidence": collected_items,
        "research_iterations": current_iterations
    }