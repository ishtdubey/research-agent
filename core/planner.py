from typing import List
from pydantic import BaseModel, Field
from state import EpistemicState
from utils.llm import get_llm
from utils.prompts import CONSTITUTION_PROMPT, EXECUTION_PROMPT

class ResearchPlanSchema(BaseModel):
    domain: str = Field(description="Classification of the query: 'empirical', 'interpretive', or 'mixed'.")
    sub_questions: List[str] = Field(description="Decomposed granular sub-questions required to answer the main prompt.")
    information_requirements: List[str] = Field(description="Specific types of data, evidence, or target literature needed.")

def planner(state: EpistemicState) -> dict:
    """
    Decomposes a research question into structured targets and sub-queries.
    Does not attempt to answer the question.
    """
    llm = get_llm(temperature=0.1)
    
    system_instruction = f"{CONSTITUTION_PROMPT}\n\n{EXECUTION_PROMPT}"
    
    planner_prompt = (
        "You are acting purely as the PLANNER stage.\n"
        f"Analyze the user's research query: '{state['query']}'\n\n"
        "Execute STEP 1: Identify Domain.\n"
        "Decompose the query into logical research steps, tracking exact items "
        "that must be gathered. Return a structured plan."
    )
    
    structured_llm = llm.with_structured_output(ResearchPlanSchema)
    
    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": planner_prompt}
    ]
    
    result = structured_llm.invoke(messages)
    
    return {
        "plan": result.sub_questions
    }