import streamlit as st
from graph import app_graph
from state import EpistemicState

# Page styling layout configuration
st.set_page_config(
    page_title="Epistemic Research Agent",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Render Sidebar Information Context
with st.sidebar:
    st.title("Epistemic Rules Engine")
    st.markdown("---")
    st.markdown(
        "This assistant operates strictly on verified pipelines. It completely "
        "bypasses standard conversational models to prioritize extreme validation, "
        "evidence tracking, and absolute clarity regarding uncertainty."
    )
    st.info(
        "Driven by Groq: Llama-3.1-70B\n\n"
        "Execution Constraint: Max 3 Research Harvesting Loops"
    )

# Primary Interface Headers
st.title("Epistemic Research Engine")
st.caption("Structured Evidence Processing Stack • Independent Step Verification")

# User input text canvas
user_query = st.text_area(
    "Enter deep investigation directive or cross-disciplinary problem statement:",
    placeholder="e.g., Examine the conflicting theories regarding quantum coherence timescales in biological microtubule systems.",
    help="Provide a research question that requires deep structural critique and source verification."
)

if st.button("Initiate Pipeline Investigation", type="primary"):
    if not user_query.strip():
        st.warning("Please enter a valid research query to kickstart the graph pipeline.")
    else:
        # 1. Initialize the global mutable state map instance
        initial_state: EpistemicState = {
            "query": user_query,
            "plan": [],
            "evidence": [],
            "extracted_claims": [],
            "critiqued_claims": {"SUPPORTED": [], "CONFLICTING": [], "INSUFFICIENT_EVIDENCE": [], "HYPOTHESIS": []},
            "supported_claims": [],
            "conflicting_claims": [],
            "unsupported_claims": [],
            "gaps": [],
            "hypotheses": [],
            "validation_status": {
                "is_valid": True,
                "traceability_passed": True,
                "unsupported_claims_removed": False,
                "uncertainty_calibrated": False,
                "errors_found": []
            },
            "final_report": "",
            "research_iterations": 0
        }
        
        # Create clear layout placeholders for runtime metrics
        status_box = st.empty()
        progress_bar = st.progress(0)
        
        # Maintain a localized tracker list to render real-time UI logging steps
        active_pipeline_log = []
        
        # 2. Execute and stream state modifications as they progress through the graph
        try:
            # We initialize a container variable to fetch the definitive output payload safely
            finalized_output_state = initial_state
            
            # Streaming loop
            for event in app_graph.stream(initial_state):
                for node_name, state_update in event.items():
                    # Format log output dynamically
                    display_name = node_name.replace("_", " ").title()
                    active_pipeline_log.append(f"✓ Node Task Completed: **{display_name}**")
                    
                    # Update localized tracker context metrics
                    with status_box.container():
                        for log_entry in active_pipeline_log:
                            st.markdown(log_entry)
                    
                    # Approximate visualization progress mappings
                    if node_name == "planner": progress_bar.progress(15)
                    elif node_name == "evidence_collection": progress_bar.progress(40)
                    elif node_name == "claim_critic": progress_bar.progress(65)
                    elif node_name == "validator": progress_bar.progress(85)
                    
                    # Record tracking step mutations locally
                    finalized_output_state = {**finalized_output_state, **state_update}

            progress_bar.progress(100)
            st.success("Investigation Pipeline Successfully Executed.")
            st.markdown("---")
            
            # 3. Output Generation Layer Layout
            st.subheader("Verified Synthesis Compilation")
            st.markdown(finalized_output_state.get("final_report", "No generated text found."))
            st.markdown("---")
            
            # 4. Audit Trail Verification Tree View Tabs
            st.subheader("Internal Epistemic Audit Logs")
            tab1, tab2, tab3 = st.tabs(["Evidence Reference Traces", "Categorized Claims", "Validator Audit"])
            
            with tab1:
                st.markdown("### Raw Evidence Gathered")
                st.write(finalized_output_state.get("evidence", []))
                
            with tab2:
                st.markdown("### Structural Categorization Matrix")
                st.write(finalized_output_state.get("critiqued_claims", {}))
                
            with tab3:
                st.markdown("### Post-Inference Guardrail Metrics")
                audit_log = finalized_output_state.get("validation_status", {})
                if audit_log.get("is_valid", True):
                    st.success("Validator status: PASSED ALL RIGOR CHECKS")
                else:
                    st.error("Validator status: ANOMALIES IDENTIFIED DURING INFERENCE")
                st.json(audit_log)
                
        except Exception as err:
            st.error(f"An execution interrupt occurred during running: {str(err)}")