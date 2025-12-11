from typing import Optional
from typing_extensions import Literal, TypedDict
from pydantic import BaseModel
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from IPython.display import Image, display

load_dotenv()
model = ChatOpenAI(model="gpt-5.1", temperature=0)

class ModerationState(TypedDict):
    content: str
    severity: Optional[Literal["safe", "questionable", "inappropriate", "harmful"]]
    action: Optional[Literal["approve", "flag", "reject", "escalate"]]
    explanation: Optional[str]
    metadata: Optional[dict]

class SeverityClassification(BaseModel):
    """Pydantic model for LLM structured output - defines what LLM returns"""
    severity: Literal["safe", "questionable", "inappropriate", "harmful"]
    explanation: str


def analyse_content(state: ModerationState) -> ModerationState:
    """
    Content Analyzer node: Pre-processes and analyzes raw content.
    Prepares content for severity classification.
    """
    content = state['content']

    if not content or len(content.strip()) == 0:
        return {
            "metadata": {"error": "Content is empty"}
        }
    
    analysis_metadata = {
        "content_length": len(content),
        "word_count": len(content.split()),
        "has_urls": any(url in content for url in ["http://", "https://"]),
    }

    return {
        "metadata": {**(state.get("metadata") or {}), **analysis_metadata}
    }

def classify_severity(state: ModerationState) -> ModerationState:
    """
    Severity Classifier node: Classifies the severity of the content.
    """
    content = state['content']
    metadata = state.get('metadata', {})
    

    metadata_str = "\n".join(f"- {k}: {v}" for k, v in metadata.items()) if metadata else "No metadata available"

    prompt = ChatPromptTemplate.from_messages([
    ("system", """
    You are a content moderation system. Classify content into EXACTLY ONE of these severity levels:

        1. safe - Content is appropriate, follows guidelines, no issues

        2. questionable - Content is borderline, may contain mild profanity or be slightly inappropriate but not clearly harmful. Examples: mild swearing, borderline language, controversial opinions.

        3. inappropriate - Content clearly violates community guidelines. Contains strong profanity, harassment, spam, or explicit content. Should be rejected. Examples: strong profanity, personal attacks, spam, explicit sexual content.

        4. harmful - Content is dangerous, illegal, or severely violates guidelines. Examples: threats, hate speech, illegal content, severe harassment, scams.

        Be strict: if content clearly violates guidelines, classify as "inappropriate", not "questionable".
    """),
        ("user", """Analyze the following content: {content}\n\nAnalysis Metadata: {metadata}
            Content: {content}
            Analysis Metadata: {metadata}
        """)
    ])
    
    chain = prompt | model.with_structured_output(SeverityClassification)
    response = chain.invoke({
        "content": content,
        "metadata": metadata_str
    })
    
    return {
        "severity": response.severity,
        "explanation": response.explanation
    }



def routing_decision(state: ModerationState) -> str:
    """
    Router node: Routes the content to the appropriate step based on the severity.
    """
    severity = state['severity']
    if severity == "safe":
        return "approve"
    elif severity == "questionable":
        return "flag"
    elif severity == "inappropriate":
        return "reject"
    elif severity == "harmful":
        return "escalate"
    else:
        return "safe"


def approve(state: ModerationState) -> ModerationState:
    original_explanation = state.get("explanation", "")
    return {
        "action": "approve",
        "explanation": f"✅ Your content has been approved and is safe to publish. No changes needed.\n\nAnalysis: {original_explanation}"
    }


def flag(state: ModerationState) -> ModerationState:
    original_explanation = state.get("explanation", "")
    return {
        "action": "flag",
        "explanation": f"⚠️ Your content was classified as questionable.\n\nReason: {original_explanation}\n\nPlease review and revise your content to make it more appropriate before resubmitting."
    }

def reject(state: ModerationState) -> ModerationState:
    original_explanation = state.get("explanation", "")
    return {
        "action": "reject",
        "explanation": f"❌ Your content was classified as inappropriate.\n\nReason: {original_explanation}\n\nIt contains content that violates our guidelines and cannot be published. Please revise your content to make it more appropriate before resubmitting."
    }

def escalate(state: ModerationState) -> ModerationState:
    original_explanation = state.get("explanation", "")
    return {
        "action": "escalate",
        "explanation": f"🚨 Your content was classified as harmful.\n\nReason: {original_explanation}\n\nThis content contains material that is dangerous, illegal, or severely violates our guidelines. This submission has been escalated for review. Please revise your content to remove any harmful material. If you believe this is an error, please contact support."
    }

graph = StateGraph(ModerationState)
graph.add_edge(START, "analyse_content")
graph.add_node("analyse_content", analyse_content)
graph.add_node("classify_severity", classify_severity)
graph.add_node("approve", approve)
graph.add_node("flag", flag)
graph.add_node("reject", reject)
graph.add_node("escalate", escalate)
graph.add_edge("analyse_content", "classify_severity")
graph.add_conditional_edges("classify_severity", routing_decision,{
    "approve": "approve",
    "flag": "flag",
    "reject": "reject",
    "escalate": "escalate"
})

graph.add_edge("approve", END)
graph.add_edge("flag", END)
graph.add_edge("reject", END)
graph.add_edge("escalate", END)

builder = graph.compile()

if __name__ == "__main__":
    graph_image = builder.get_graph().draw_mermaid_png()
    with open("graph.png", "wb") as f:
        f.write(graph_image)
    print("Graph saved to graph.png")
