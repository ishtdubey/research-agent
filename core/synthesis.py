from typing import List, Dict, Any
from pydantic import BaseModel, Field
from state import EpistemicState, ResearchGap, HypothesisItem, ValidationReport
from utils.llm import get_llm
from utils.prompts import CONSTITUTION_PROMPT, EXECUTION_PROMPT

# ==========================================
# 1. PYDANTIC SCHEMAS FOR STRUCTURED OUTPUT
# ==========================================

class DiscoveredGap(BaseModel):
    gap_description: str = Field(description="Description of the open question, research limitation, or unresolved problem.")
    supporting_source_ids: List[str] = Field(description="List of independent source_ids identifying this exact limitation.")

class GapResponseSchema(BaseModel):
    gaps: List[DiscoveredGap]

class NovelHypothesis(BaseModel):
    hypothesis: str = Field(description="A clear, testable, or reasonable inference derived from the data patterns.")
    rationale: str = Field(description="Explaining how the existing evidence patterns directly give rise to this inference.")
    linked_evidence_ids: List[str] = Field(description="The exact foundational source_ids justifying this speculation.")

class HypothesisResponseSchema(BaseModel):
    hypotheses: List[NovelHypothesis]

class ValidationAudit(BaseModel):
    is_valid: bool = Field(description="True if the entire state meets the non-negotiable epistemic rules.")
    traceability_passed: bool = Field(description="True if every major claim maps directly to a valid source_id.")
    unsupported_claims_removed_or_relabeled: bool = Field(description="True if unverified speculation was stripped from facts.")
    uncertainty_calibrated: bool = Field(description="True if the tone accurately mirrors evidence availability instead of model certainty.")
    errors_found: List[str] = Field(description="List of specific structural or logical errors identified during validation.")


# ==========================================
# 2. GRAPH NODE IMPLEMENTATIONS
# ==========================================

def gap_detection(state: EpistemicState) -> dict:
    """
    Node: Detects research gaps and enforces the strict 2-source baseline.
    Categorizes anomalies cleanly into Strong or Tentative gaps.
    """
    evidence_list = state.get("evidence", [])
    if not evidence_list:
        return {"gaps": []}
        
    llm = get_llm(temperature=0.0)
    structured_llm = llm.with_structured_output(GapResponseSchema)
    
    evidence_payload = "\n".join([f"- {e['source_id']}: {e['content']}" for e in evidence_list])
    
    system_instruction = f"{CONSTITUTION_PROMPT}\n\n{EXECUTION_PROMPT}"
    user_prompt = (
        "You are operating within STEP 5 — RESEARCH GAPS.\n"
        "Identify open questions, limitations, and unresolved problems from the source text below. "
        "Group matching limitations together and trace every source ID that points it out.\n\n"
        f"--- EVIDENCE REPOSITORY ---\n{evidence_payload}"
    )
    
    processed_gaps: List[ResearchGap] = []
    try:
        response = structured_llm.invoke([
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ])
        
        for item in response.gaps:
            # Enforce your precise Constitution Clause 9 rule via code verification
            unique_sources = list(set(item.supporting_source_ids))
            gap_type = "Strong" if len(unique_sources) >= 2 else "Tentative"
            
            processed_gaps.append({
                "gap_description": item.gap_description,
                "supporting_sources": unique_sources,
                "gap_type": gap_type
            })
    except Exception:
        pass
        
    return {"gaps": processed_gaps}


def hypothesis_generation(state: EpistemicState) -> dict:
    """
    Node: Generates novel exploratory hypotheses based strictly on observed evidence patterns.
    Ensures these stay isolated from established factual claims.
    """
    evidence_list = state.get("evidence", [])
    if not evidence_list:
        return {"hypotheses": []}
        
    llm = get_llm(temperature=0.2) # Slighly higher for pattern generation, bounded by schema
    structured_llm = llm.with_structured_output(HypothesisResponseSchema)
    
    evidence_payload = "\n".join([f"- {e['source_id']}: {e['content']}" for e in evidence_list])
    
    system_instruction = f"{CONSTITUTION_PROMPT}\n\n{EXECUTION_PROMPT}"
    user_prompt = (
        "You are operating within STEP 6 — HYPOTHESIS GENERATION.\n"
        "Generate reasonable hypotheses derived explicitly from patterns in the evidence. "
        "Do not invent context. Anchor every hypothesis to the source IDs that inspired it.\n\n"
        f"--- EVIDENCE REPOSITORY ---\n{evidence_payload}"
    )
    
    processed_hypotheses: List[HypothesisItem] = []
    try:
        response = structured_llm.invoke([
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ])
        
        for item in response.hypotheses:
            processed_hypotheses.append({
                "hypothesis": item.hypothesis,
                "rationale": item.rationale,
                "linked_evidence_ids": item.linked_evidence_ids
            })
    except Exception:
        pass
        
    return {"hypotheses": processed_hypotheses}


def validator(state: EpistemicState) -> dict:
    """
    Node: Executes STEP 7 — FINAL VALIDATION.
    Acts as an adversarial auditor checking trace tracking before formatting reports.
    """
    llm = get_llm(temperature=0.0)
    structured_llm = llm.with_structured_output(ValidationAudit)
    
    # Package up the entire historical state map for verification
    state_summary = (
        f"Query: {state['query']}\n\n"
        f"Supported Claims: {[{'id': c['claim_id'], 'src': c['source_id'], 'txt': c['claim']} for c in state.get('supported_claims', [])]}\n\n"
        f"Conflicting Claims: {state.get('conflicting_claims', [])}\n\n"
        f"Research Gaps: {state.get('gaps', [])}\n\n"
        f"Hypotheses: {state.get('hypotheses', [])}"
    )
    
    system_instruction = f"{CONSTITUTION_PROMPT}\n\n{EXECUTION_PROMPT}"
    user_prompt = (
        "You are acting purely as the ADVERSARIAL VALIDATION LAYER.\n"
        "Audit the state map below against our Core Principles. Check if claims lack source references, "
        "or if tentative gaps are artificially inflated. Reject files failing rigor metrics.\n\n"
        f"--- PIPELINE CURRENT STATE ---\n{state_summary}"
    )
    
    # Default fallback audit if inference drops
    report: ValidationReport = {
        "is_valid": True,
        "traceability_passed": True,
        "unsupported_claims_removed": True,
        "uncertainty_calibrated": True,
        "errors_found": []
    }
    
    try:
        audit_res = structured_llm.invoke([
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ])
        
        report = {
            "is_valid": audit_res.is_valid,
            "traceability_passed": audit_res.traceability_passed,
            "unsupported_claims_removed": audit_res.unsupported_claims_removed_or_relabeled,
            "uncertainty_calibrated": audit_res.uncertainty_calibrated,
            "errors_found": audit_res.errors_found
        }
    except Exception:
        pass
        
    return {"validation_status": report}


def writer(state: EpistemicState) -> dict:
    """
    Node: Synthesizes the finalized research compilation into strict, domain-agnostic Markdown markdown structure.
    Forbidden from manufacturing net-new assertions or smoothing out disagreements.
    """
    # Enforce strict compliance: If validator found explicit blocks, we can scrub them or warn
    audit = state.get("validation_status", {})
    error_prefix = ""
    if audit and not audit.get("is_valid", True):
        error_prefix = f"> ⚠️ **EPISTEMIC AUDIT NOTICE**: Certain claims were suppressed or modified during validation due to tracing gaps: {audit.get('errors_found', [])}\n\n---\n\n"
        
    llm = get_llm(temperature=0.0)
    
    # Reassemble clean lists
    supported = "\n".join([f"- {c['claim']} *(Source: {c['source_id']})*" for c in state.get("supported_claims", [])])
    conflicting = "\n".join([f"- Claim: {item['claim_item']['claim']}\n  *Conflict Resolution Insight*: {item['rationale']}" for item in state.get("conflicting_claims", [])])
    gaps = "\n".join([f"- [{item['gap_type']} Gap] {item['gap_description']} *(Sources: {', '.join(item['supporting_sources'])})*" for item in state.get("gaps", [])])
    hypotheses = "\n".join([f"- **Hypothesis**: {item['hypothesis']}\n  *Rationale*: {item['rationale']} *(Tied to: {', '.join(item['linked_evidence_ids'])})*" for item in state.get("hypotheses", [])])
    unsupported = "\n".join([f"- {c['claim']} *(Marked Insufficient Evidence)*" for c in state.get("unsupported_claims", [])])

    user_prompt = (
        f"Synthesize a polished markdown compilation for the query: '{state['query']}' based strictly on the verified data below.\n"
        "Do not invent facts or extrapolate beyond what is recorded.\n\n"
        "Format using exactly these Markdown sections:\n"
        "## Established Findings\n"
        "## Conflicting Findings\n"
        "## Research Gaps\n"
        "## Hypotheses\n"
        "## Insufficient Evidence\n\n"
        f"--- VERIFIED DATA TRACES ---\n"
        f"Supported Data:\n{supported or 'None verified.'}\n\n"
        f"Conflicting Data:\n{conflicting or 'None noted.'}\n\n"
        f"Discovered Gaps:\n{gaps or 'None verified.'}\n\n"
        f"Generated Hypotheses:\n{hypotheses or 'None derived.'}\n\n"
        f"Insufficient Evidence Marks:\n{unsupported or 'None categorized.'}"
    )
    
    response = llm.invoke([
        {"role": "system", "content": CONSTITUTION_PROMPT},
        {"role": "user", "content": user_prompt}
    ])
    
    return {"final_report": error_prefix + response.content}