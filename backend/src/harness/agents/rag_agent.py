import json
from google.adk.agents import LlmAgent

DOCUMENTS = [
    {
        "id": "doc-1",
        "title": "What is FastAPI?",
        "content": "FastAPI is a modern, high-performance web framework for building APIs with Python based on standard Python type hints. It was created by Sebastián Ramírez and first released in 2018. FastAPI is built on top of Starlette for the web parts and Pydantic for the data parts.",
    },
    {
        "id": "doc-2",
        "title": "What is SQLAlchemy?",
        "content": "SQLAlchemy is the Python SQL toolkit and Object-Relational Mapping (ORM) library. It provides a full suite of well-known enterprise-level persistence patterns. SQLAlchemy 2.0 introduced a new unified interface with improved type support.",
    },
    {
        "id": "doc-3",
        "title": "What is OpenTelemetry?",
        "content": "OpenTelemetry is an open-source observability framework for generating, collecting, and exporting telemetry data (traces, metrics, logs). It is a CNCF project. The GenAI semantic conventions add LLM-specific attributes like gen_ai.request.model and gen_ai.usage.input_tokens.",
    },
    {
        "id": "doc-4",
        "title": "What is Google ADK?",
        "content": "Google Agent Development Kit (ADK) is an open-source, Apache-2.0 agent framework supporting Python, TypeScript, Go, and Java. Released at Google Cloud NEXT on April 9, 2025. ADK 2.0 adds a graph-based Workflow Runtime for routing, fan-out/fan-in, loops, retry, and human-in-the-loop.",
    },
    {
        "id": "doc-5",
        "title": "What are LLM Evals?",
        "content": "LLM evaluations (evals) are systematic assessments of language model outputs against defined criteria. Common metrics include faithfulness, relevancy, and hallucination detection. Evals can be automated using LLM-as-judge approaches or rule-based metrics like ROUGE scores.",
    },
]


def retrieve_documents(query: str) -> str:
    """Search the document knowledge base and return relevant documents."""
    query_lower = query.lower()
    results = []
    for doc in DOCUMENTS:
        if any(
            word in doc["title"].lower() or word in doc["content"].lower()
            for word in query_lower.split()
        ):
            results.append(doc)
    if not results:
        results = [DOCUMENTS[0]]
    return json.dumps(results[:3])


RAG_INSTRUCTION = """You are a knowledgeable assistant that answers questions using retrieved documents.
Always use the retrieve_documents tool to search for relevant information before answering.
Base your answer ONLY on the retrieved documents. Do not make up information.
If the documents don't contain the answer, say so clearly."""


def create_rag_agent(model: str = "gemini-2.5-flash") -> LlmAgent:
    return LlmAgent(
        name="rag_agent",
        model=model,
        instruction=RAG_INSTRUCTION,
        tools=[retrieve_documents],
    )
