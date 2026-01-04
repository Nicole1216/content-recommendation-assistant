"""Sales Enablement Assistant - Streamlit App."""

import streamlit as st
import os
from config.settings import Settings
from schemas.context import AudiencePersona
from orchestrator import SalesEnablementOrchestrator


st.set_page_config(
    page_title="Sales Enablement Assistant",
    page_icon="💼",
    layout="wide"
)

st.title("Sales Enablement Assistant")
st.markdown("AI-powered sales support for Udacity Enterprise")

# Sidebar configuration
st.sidebar.header("Configuration")

persona_option = st.sidebar.selectbox(
    "Target Audience Persona",
    options=["CTO", "HR", "L&D"],
    index=0
)

top_k = st.sidebar.slider(
    "Number of results to retrieve",
    min_value=1,
    max_value=10,
    value=5
)

catalog_api_url = st.sidebar.text_input(
    "Catalog API URL (optional)",
    value=os.environ.get("CATALOG_API_URL", ""),
    help="Leave empty to use mock data"
)

csv_path = st.sidebar.text_input(
    "CSV Path",
    value="data/NLC_Skill_Data.csv",
    help="Path to CSV file for data source"
)

# Map persona string to enum
persona_map = {
    "CTO": AudiencePersona.CTO,
    "HR": AudiencePersona.HR,
    "L&D": AudiencePersona.L_AND_D,
}

# Main input
question = st.text_area(
    "Enter your sales question:",
    placeholder="e.g., What courses do we offer for AI and machine learning?",
    height=100
)

if st.button("Get Answer", type="primary"):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Processing your question..."):
            try:
                settings = Settings(
                    catalog_api_url=catalog_api_url if catalog_api_url else None,
                    csv_path=csv_path if csv_path else None,
                    top_k=top_k,
                    verbose=False,
                )

                orchestrator = SalesEnablementOrchestrator(settings=settings)
                persona = persona_map[persona_option]

                response = orchestrator.process_question(question, persona)

                st.success("Response generated!")
                st.markdown("---")
                st.markdown("### Answer")
                st.markdown(response)

            except Exception as e:
                st.error(f"Error processing question: {e}")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("Built with Streamlit")
