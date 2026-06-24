from typing import List, Dict, Any, Literal
from pydantic import BaseModel, Field
from state import EpistemicState, ExtractedClaim, CritiquedClaims
from utils.llm import get_llm
from utils.prompts import CONSTITUTION_PROMPT, EXECUTION_PROMPT

# ==========================================
# 1. PYDANTIC SCHEMAS FOR STRUCTURED OUTPUT
# ==========================================

class ExtractedClaimSchema(BaseModel):
    claim: str = Field(description="A distinct, non-trivial factual claim extracted from the source content.")
    source_id: str = Field(description="The exact source_id (e.g., 'src_001') this claim originated from.")
    context: str = Field(description="The verbatim or near-verbatim textual snippet surrounding the claim for reference verification.")

class ExtractionResponseSchema(BaseModel):
    claims: List[ExtractedClaimSchema]

class SingleClaimCritique(BaseModel):
    claim_id: str = Field(description="The unique ID of the claim being evaluated (e.g., 'claim_001').")
    category: Literal["SUPPORTED", "CONFLICTING", "INSUFFICIENT_EVIDENCE", "HYPOTHESIS"] = Field(
        description="The strict classification based on evidence quality definitions."
    )
    brief_rationale: str = Field(description="A brief explanation of why this specific category fits the current body of evidence.")

class CritiqueResponseSchema(BaseModel):
    critiques: List[SingleClaimCritique]

class CoverageAssessmentSchema(BaseModel):
    needs_more_research: bool = Field(description="Set to true ONLY if critical elements of the core query remain completely unaddressed.")
    rationale: str = Field(description="Epistemic reasoning behind deciding to wrap up or proceed with deeper web harvesting loops.")


# ==========================================
# 2. GRAPH NODE IMPLEMENTATIONS
# ==========================================

def claim_extraction(state: EpistemicState) -> dict:
    """
    Node: Parse all gathered evidence items to extract atomic claims.
    Maintains direct trace context IDs to fulfill the EVIDENCE FIRST directive.
    """
    evidence_list = state.get("evidence", [])
    if not evidence_list:
        return {"extracted_claims": []}
        
    llm = get_llm(temperature=0.0)
    structured_llm = llm.with_structured_output(ExtractionResponseSchema)
    
    # Format the collected evidence payload neatly for processing
    evidence_payload = "\n\n".join([
        f"Source ID: {item['source_id']}\nTitle: {item['title']}\nContent: {item['content']}"
        for item in evidence_list
    ])
    
    system_instruction = f"{CONSTITUTION_PROMPT}\n\n{EXECUTION_PROMPT}"
    user_prompt = (
        "You are operating within STEP 3 — EXTRACT CLAIMS.\n"
        "Review the provided evidence repository below and extract major non-trivial claims. "
        "Every single extracted claim must carry the exact matching Source ID from which it was found.\n\n"
        f"--- EVIDENCE REPOSITORY ---\n{evidence_payload}"
    )
    
    try:
        response = structured_llm.invoke([
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ])
        
        # Map back to structural dictionary matching EpistemicState
        processed_claims: List[ExtractedClaim] = []
        for idx, item in enumerate(response.claims):
            processed_claims.append({
                "claim_id": f"claim_{idx+1:03d}",
                "claim": item.claim,
                "source_id": item.source_id,
                "context": item.context
            })
        return {"extracted_claims": processed_claims}
    except Exception:
        # Fallback empty initialization to keep graph pipeline safe
        return {"extracted_claims": []}


def claim_critic(state: EpistemicState) -> dict:
    """
    Node: Evaluates the validation tier of every single extracted claim against the global state content.
    Enforces cross-referencing and maps categories cleanly into standard properties.
    """
    claims = state.get("extracted_claims", [])
    evidence_list = state.get("evidence", [])
    
    if not claims:
        empty_critique: CritiquedClaims = {"SUPPORTED": [], "CONFLICTING": [], "INSUFFICIENT_EVIDENCE": [], "HYPOTHESIS": []}
        return {"critiqued_claims": empty_critique, "supported_claims": [], "conflicting_claims": [], "unsupported_claims": []}
        
    llm = get_llm(temperature=0.0)
    structured_llm = llm.with_structured_output(CritiqueResponseSchema)
    
    # Pack up references for cross-claim evaluation
    claims_payload = "\n".join([f"- [{c['claim_id']}] (From {c['source_id']}): {c['claim']}" for c in claims])
    evidence_payload = "\n".join([f"- {e['source_id']}: {e['content']}" for e in evidence_list])
    
    system_instruction = f"{CONSTITUTION_PROMPT}\n\n{EXECUTION_PROMPT}"
    user_prompt = (
        "You are operating within STEP 4 — CRITIQUE CLAIMS.\n"
        "Classify each of the extracted claims into exactly one category based strictly on the evidence given.\n\n"
        f"--- EXTRACTED CLAIMS ---\n{claims_payload}\n\n"
        f"--- GLOBAL EVIDENCE FOR VERIFICATION ---\n{evidence_payload}"
    )
    
    # Initialize containers
    critiqued_bucket: CritiquedClaims = {"SUPPORTED": [], "CONFLICTING": [], "INSUFFICIENT_EVIDENCE": [], "HYPOTHESIS": []}
    supported_list: List[ExtractedClaim] = []
    conflicting_list: List[Dict[str, Any]] = []
    unsupported_list: List[ExtractedClaim] = []
    
    try:
        response = structured_llm.invoke([
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ])
        
        # Build lookup table for efficiency
        claim_map = {c["claim_id"]: c for c in claims}
        
        for item in response.critiques:
            target_claim = claim_map.get(item.claim_id)
            if not target_claim:
                continue
                
            cat = item.category
            if cat == "SUPPORTED":
                critiqued_bucket["SUPPORTED"].append(target_claim)
                supported_list.append(target_claim)
            elif cat == "CONFLICTING":
                conflict_item = {"claim_item": target_claim, "rationale": item.brief_rationale}
                critiqued_bucket["CONFLICTING"].append(conflict_item)
                conflicting_list.append(conflict_item)
            elif cat == "INSUFFICIENT_EVIDENCE":
                critiqued_bucket["INSUFFICIENT_EVIDENCE"].append(target_claim)
                unsupported_list.append(target_claim)
            elif cat == "HYPOTHESIS":
                critiqued_bucket["HYPOTHESIS"].append(target_claim)
                unsupported_list.append(target_claim) # Kept here until synthesized safely
                
    except Exception:
        pass

    return {
        "critiqued_claims": critiqued_bucket,
        "supported_claims": supported_list,
        "conflicting_claims": conflicting_list,
        "unsupported_claims": unsupported_list
    }


# ==========================================
# 3. CONDITIONAL ROUTER (THE GATEKEEPER)
# ==========================================

def coverage_critic(state: EpistemicState) -> str:
    """
    Conditional Routing Function: Decides loop-back mechanics based on target verification criteria.
    Only allows loops if loops remain inside safety thresholds (< 3 iterations).
    """
    iterations = state.get("research_iterations", 0)
    if iterations >= 3:
        # Enforce maximum workflow path predictability (Hard Stop)
        return "proceed"
        
    llm = get_llm(temperature=0.0)
    structured_llm = llm.with_structured_output(CoverageAssessmentSchema)
    
    system_instruction = f"{CONSTITUTION_PROMPT}\n\n{EXECUTION_PROMPT}"
    user_prompt = (
        "You are executing the Coverage Critic verification phase.\n"
        f"Original User Intent: '{state['query']}'\n"
        f"Current Sub-questions Explored: {state.get('plan', [])}\n"
        f"Total Unique Evidence Count Gathered: {len(state.get('evidence', []))}\n\n"
        "Determine if vital angles of the user's intent are completely unexamined, "
        "requiring another discovery iteration. Be highly conservative."
    )
    
    try:
        assessment = structured_llm.invoke([
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ])
        
        if assessment.needs_more_research:
            return "research_more"
    except Exception:
        pass
        
    return "proceed"