import os
import streamlit as st
from retrieval.real_csv_provider import RealCSVProvider
from retrieval.catalog_api_provider import CatalogAPIProvider
from orchestrator import Orchestrator

st.set_page_config(page_title="Content Recommendation Assistant", layout="wide")

st.title("📚 Content Recommendation Assistant")
st.caption("Demo: Unified Catalog API + Skill-aware CSV evidence")

question = st.text_input(
    "What are you looking for?",
    placeholder="e.g. Do we have GenAI training for business leaders?"
)

persona = st.selectbox(
    "Persona",
    ["Sales", "HR", "CTO", "Marketing", "Executive"],
    index=1
)

run = st.button("🔍 Find Recommendations")

if run and question:
    with st.spinner("Searching catalog and validating with CSV..."):
        orchestrator = Orchestrator(
            catalog_provider=CatalogAPIProvider(
                base_url=os.environ["CATALOG_API_URL"]
            ),
            csv_provider=RealCSVProvider("data/NLC_Skill_Data.csv")
        )

        result = orchestrator.run(
            question=question,
            persona=persona
        )

    st.subheader("Results")

    for i, rec in enumerate(result.recommendations, 1):
        st.markdown(f"### {i}. {rec.program_title}")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Catalog Evidence**")
            st.json(rec.catalog_evidence or {})

        with col2:
            st.markdown("**CSV Skill Evidence**")
            st.write(rec.csv_evidence or [])

        st.markdown("---")
