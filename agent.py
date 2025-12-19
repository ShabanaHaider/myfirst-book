"""
Gemini Agent Configuration for RAG Chatbot

This module initializes and configures the Gemini agent using the OpenAI-compatible API.
"""
from dotenv import load_dotenv
import os
from openai import AsyncOpenAI
from src.config.settings import settings


def initialize_gemini_agent():
    """
    Initialize the Gemini agent using OpenAI-compatible API.

    Returns:
        AsyncOpenAI: Configured client for Gemini API
    """
    # Load environment variables if not already loaded
    load_dotenv()

    # Validate that GEMINI_API_KEY is set
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set in environment variables")

    # Create AsyncOpenAI client pointing to Gemini endpoint
    gemini_client = AsyncOpenAI(
        api_key=settings.GEMINI_API_KEY,
        base_url=settings.LLM_BASE_URL,
    )

    return gemini_client


def get_gemini_completion(client: AsyncOpenAI, prompt: str, model: str = None):
    """
    Get completion from Gemini model.

    Args:
        client: Configured AsyncOpenAI client for Gemini
        prompt: The input prompt for the model
        model: Model name to use (defaults to settings.LLM_MODEL_NAME)

    Returns:
        str: The model's response
    """
    if model is None:
        model = settings.LLM_MODEL_NAME

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
    )

    return response.choices[0].message.content


async def get_gemini_completion_async(client: AsyncOpenAI, prompt: str, model: str = None):
    """
    Get completion from Gemini model asynchronously.

    Args:
        client: Configured AsyncOpenAI client for Gemini
        prompt: The input prompt for the model
        model: Model name to use (defaults to settings.LLM_MODEL_NAME)

    Returns:
        str: The model's response
    """
    if model is None:
        model = settings.LLM_MODEL_NAME

    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
    )
    return response.choices[0].message.content


# Initialize the agent when module is imported
gemini_agent = initialize_gemini_agent()


if __name__ == "__main__":
    # Example usage
    print("Gemini Agent initialized successfully!")
    print(f"Model: {settings.LLM_MODEL_NAME}")
    print(f"Temperature: {settings.LLM_TEMPERATURE}")
    print(f"Max Tokens: {settings.LLM_MAX_TOKENS}")

    # Test the agent with a simple prompt
    try:
        test_prompt = "Hello, this is a test. Please respond with a brief greeting."
        response = get_gemini_completion(gemini_agent, test_prompt)
        print(f"Test response: {response}")
    except Exception as e:
        print(f"Error during test: {e}")