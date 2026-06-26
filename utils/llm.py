import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

def get_llm(temperature: float = 0.0) -> ChatGroq:
    """
    Instantiates the Groq client using the Llama-3.1-70b-versatile architecture.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("CRITICAL: GROQ_API_KEY is missing from your environment setup.")
        
    return ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=temperature,
        api_key=api_key
    )