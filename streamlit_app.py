"""Sales Enablement Assistant - Streamlit App with Chat UI."""

import os
import uuid
import streamlit as st
from config.settings import Settings
from schemas.context import AudiencePersona
from orchestrator import SalesEnablementOrchestrator


st.set_page_config(
    page_title="Sales Enablement Assistant",
    page_icon="💼",
    layout="wide"
)

# Initialize session state
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = None


def reset_conversation():
    """Reset conversation state."""
    st.session_state.conversation_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.orchestrator = None


def get_orchestrator(settings: Settings) -> SalesEnablementOrchestrator:
    """Get or create orchestrator instance."""
    if st.session_state.orchestrator is None:
        st.session_state.orchestrator = SalesEnablementOrchestrator(settings=settings)
    return st.session_state.orchestrator


# Sidebar configuration
st.sidebar.header("Configuration")

# Company name input
company_name = st.sidebar.text_input(
    "Customer Company Name",
    value="",
    placeholder="e.g., Acme Corp",
    help="Enter the customer's company name for context"
)

st.sidebar.markdown("---")

# LLM Provider selection
llm_provider = st.sidebar.selectbox(
    "LLM Provider",
    options=["openai", "anthropic"],
    index=0,
    help="Select which LLM to use for reasoning"
)

# API Keys
openai_api_key = st.sidebar.text_input(
    "OpenAI API Key",
    value=os.environ.get("OPENAI_API_KEY", ""),
    type="password",
    help="Required for OpenAI provider and semantic search"
)

anthropic_api_key = st.sidebar.text_input(
    "Anthropic API Key",
    value=os.environ.get("ANTHROPIC_API_KEY", ""),
    type="password",
    help="Required for Anthropic provider"
)

st.sidebar.markdown("---")

# Persona selection
persona_option = st.sidebar.selectbox(
    "Target Audience Persona",
    options=["CTO", "HR", "L&D"],
    index=0,
    help="Who is the customer contact?"
)

# Map persona string to enum
persona_map = {
    "CTO": AudiencePersona.CTO,
    "HR": AudiencePersona.HR,
    "L&D": AudiencePersona.L_AND_D,
}

st.sidebar.markdown("---")

# Advanced settings
with st.sidebar.expander("Advanced Settings"):
    top_k = st.slider(
        "Number of results to retrieve",
        min_value=1,
        max_value=10,
        value=5
    )

    csv_path = st.text_input(
        "CSV Data Path",
        value="data/Udacity_Content_Catalog_Skill.csv",
        help="Path to CSV file containing program data"
    )

    memory_enabled = st.checkbox(
        "Enable Memory",
        value=True,
        help="Track conversation history"
    )

    react_enabled = st.checkbox(
        "Enable ReAct Loop",
        value=True,
        help="Use iterative reasoning for evidence gathering"
    )

    max_react_iterations = st.slider(
        "Max ReAct Iterations",
        min_value=1,
        max_value=10,
        value=5
    )

    show_debug = st.checkbox("Show debug info", value=False)

# New Conversation button
if st.sidebar.button("Start New Conversation", type="secondary"):
    reset_conversation()
    st.rerun()

# Display conversation info
st.sidebar.markdown("---")
st.sidebar.caption(f"Conversation ID: {st.session_state.conversation_id[:8]}...")
if company_name:
    st.sidebar.caption(f"Customer: {company_name}")

# Main content
st.title("Sales Enablement Assistant")
st.markdown("AI-powered sales support for Udacity Enterprise")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask a question about Udacity programs..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Build settings
                settings = Settings(
                    csv_path=csv_path,
                    llm_provider=llm_provider,
                    openai_api_key=openai_api_key if openai_api_key else None,
                    anthropic_api_key=anthropic_api_key if anthropic_api_key else None,
                    top_k=top_k,
                    memory_enabled=memory_enabled,
                    react_enabled=react_enabled,
                    max_react_iterations=max_react_iterations,
                    verbose=show_debug,
                )

                # Get orchestrator
                orchestrator = get_orchestrator(settings)
                persona = persona_map[persona_option]

                # Debug info
                if show_debug:
                    st.info(f"LLM Provider: {llm_provider}")
                    st.info(f"CSV Path: {csv_path}")
                    st.info(f"Programs loaded: {len(orchestrator.csv_provider.programs)}")

                    llm_status = "Enabled" if orchestrator.llm_client else "Disabled (fallback mode)"
                    st.info(f"LLM: {llm_status}")

                    memory_status = "Enabled" if orchestrator.memory_store else "Disabled"
                    st.info(f"Memory: {memory_status}")

                    react_status = "Enabled" if orchestrator.react_loop else "Disabled"
                    st.info(f"ReAct Loop: {react_status}")

                    embeddings_status = "Enabled" if (
                        orchestrator.csv_provider.embeddings_manager and
                        orchestrator.csv_provider.embeddings_manager.is_available()
                    ) else "Disabled (keyword search only)"
                    st.info(f"Semantic Search: {embeddings_status}")

                # Process question
                response = orchestrator.process_question(
                    question=prompt,
                    persona=persona,
                    conversation_id=st.session_state.conversation_id,
                    company_name=company_name if company_name else None
                )

                # Display response
                st.markdown(response)

                # Add assistant message to chat history
                st.session_state.messages.append({"role": "assistant", "content": response})

            except Exception as e:
                error_msg = f"Error processing question: {e}"
                st.error(error_msg)
                if show_debug:
                    import traceback
                    st.code(traceback.format_exc())
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

# Welcome message if no messages
if not st.session_state.messages:
    st.markdown("""
    ### Welcome!

    I'm your Sales Enablement Assistant. I can help you answer customer questions about Udacity programs.

    **Try asking:**
    - "What programs do we have for machine learning and deep learning?"
    - "How can we help a team of data analysts transition to data scientists?"
    - "What Python and SQL courses are available for beginners?"

    **Tips:**
    - Enter the customer's company name in the sidebar for personalized responses
    - Select the appropriate persona (CTO, HR, L&D) for tailored messaging
    - The conversation history is preserved - ask follow-up questions!
    """)

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("Built with Streamlit")
