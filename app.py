import streamlit as st
from main import builder


st.set_page_config(
    page_title="Content Moderation System",
    page_icon="🛡️",
    layout="wide"
)

if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

def run_moderation(content: str):
    """
    Run content through moderation workflow
    """
    try:
        result = builder.invoke({"content": content})
        return result
    except Exception as e:
        return {"error": str(e)}

def main():
    st.title("Content Moderation System")
    st.markdown("Submit your content for moderation. You'll receive feedback and can revise your content.")
    
    with st.sidebar:
        st.header("Instructions")
        st.markdown("""
        1. Enter your content in the text area below
        2. Click **Submit** to analyze your content
        3. Review the moderation result
        4. If flagged, revise your content and resubmit
        5. Continue until your content is approved
        """)
        
        st.header("Severity Levels")
        st.markdown("""
        - **✅ Safe**: Content approved
        - **⚠️ Questionable**: Borderline, needs review
        - **❌ Inappropriate**: Violates guidelines
        - **🚨 Harmful**: Dangerous content
        """)
        

        if st.button("Clear Conversation"):
            st.session_state.messages = []
            st.session_state.conversation_history = []
            st.rerun()
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            if "metadata" in message and message["metadata"]:
                with st.expander("📊 Analysis Details"):
                    st.json(message["metadata"])
    
    if prompt := st.chat_input("Enter your content here..."):
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
            "metadata": None
        })
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Analyzing content..."):
                result = run_moderation(prompt)
            
            if "error" in result:
                st.error(f"Error: {result['error']}")
            else:
                severity = result.get("severity", "unknown")
                action = result.get("action", "unknown")
                explanation = result.get("explanation", "No explanation provided")
                metadata = result.get("metadata", {})
                
                if action == "approve":
                    st.success(explanation)
                elif action == "flag":
                    st.warning(explanation)
                elif action == "reject":
                    st.error(explanation)
                elif action == "escalate":
                    st.error(explanation)
                else:
                    st.info(explanation)
                
                with st.expander("Analysis Details"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Severity", severity.upper())
                        st.metric("Action", action.upper())
                    with col2:
                        if metadata:
                            st.write("**Metadata:**")
                            st.json(metadata)
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": explanation,
                    "metadata": {
                        "severity": severity,
                        "action": action,
                        "full_metadata": metadata
                    }
                })
                
                st.session_state.conversation_history.append({
                    "user_input": prompt,
                    "severity": severity,
                    "action": action,
                    "explanation": explanation,
                    "metadata": metadata
                })

if __name__ == "__main__":
    main()

