"""
OpenAI-Compatible Client Wrapper for Gemini

This module provides a client wrapper for interacting with the Gemini API
through the OpenAI-compatible interface.
"""
from typing import Optional, Dict, Any, List, Union
import logging
from openai import AsyncOpenAI, OpenAI
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion import Choice
from pydantic import BaseModel, Field
from src.config.settings import settings


class OpenAIClientConfig(BaseModel):
    """Configuration model for the OpenAI client."""
    api_key: str = Field(..., description="API key for authentication")
    base_url: str = Field(..., description="Base URL for the API")
    timeout: float = Field(30.0, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of retries for failed requests")


class OpenAIClientWrapper:
    """
    Wrapper for OpenAI client that provides additional functionality
    and error handling for Gemini API interactions.
    """

    def __init__(self, config: Optional[OpenAIClientConfig] = None):
        """
        Initialize the OpenAI client wrapper.

        Args:
            config: Configuration for the client (uses settings if not provided)
        """
        self.logger = logging.getLogger(__name__)

        if config is None:
            # Use settings configuration
            if not settings.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY is not set in settings")

            config = OpenAIClientConfig(
                api_key=settings.GEMINI_API_KEY,
                base_url=settings.LLM_BASE_URL,
                timeout=30.0,
                max_retries=3
            )

        self.config = config
        self._async_client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
            max_retries=config.max_retries
        )
        self._sync_client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
            max_retries=config.max_retries
        )

    @property
    def async_client(self) -> AsyncOpenAI:
        """Get the async OpenAI client."""
        return self._async_client

    @property
    def sync_client(self) -> OpenAI:
        """Get the sync OpenAI client."""
        return self._sync_client

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        **kwargs
    ) -> ChatCompletion:
        """
        Generate a response from the LLM.

        Args:
            messages: List of messages in the conversation (role, content)
            model: Model name to use (defaults to settings)
            temperature: Temperature for response randomness (defaults to settings)
            max_tokens: Maximum tokens in response (defaults to settings)
            **kwargs: Additional parameters to pass to the API

        Returns:
            ChatCompletion: The response from the LLM
        """
        if model is None:
            model = settings.LLM_MODEL_NAME

        if temperature is None:
            temperature = settings.LLM_TEMPERATURE

        if max_tokens is None:
            max_tokens = settings.LLM_MAX_TOKENS

        try:
            response = await self._async_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            self.logger.info(f"Successfully generated response from model: {model}")
            return response

        except Exception as e:
            self.logger.error(f"Error generating response from model {model}: {str(e)}", exc_info=True)
            raise

    def generate_response_sync(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        **kwargs
    ) -> ChatCompletion:
        """
        Generate a response from the LLM synchronously.

        Args:
            messages: List of messages in the conversation (role, content)
            model: Model name to use (defaults to settings)
            temperature: Temperature for response randomness (defaults to settings)
            max_tokens: Maximum tokens in response (defaults to settings)
            **kwargs: Additional parameters to pass to the API

        Returns:
            ChatCompletion: The response from the LLM
        """
        if model is None:
            model = settings.LLM_MODEL_NAME

        if temperature is None:
            temperature = settings.LLM_TEMPERATURE

        if max_tokens is None:
            max_tokens = settings.LLM_MAX_TOKENS

        try:
            response = self._sync_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            self.logger.info(f"Successfully generated sync response from model: {model}")
            return response

        except Exception as e:
            self.logger.error(f"Error generating sync response from model {model}: {str(e)}", exc_info=True)
            raise

    async def validate_api_key(self) -> bool:
        """
        Validate the API key by making a simple test request.

        Returns:
            bool: True if the API key is valid, False otherwise
        """
        try:
            # Make a simple test request
            test_response = await self._async_client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=5
            )

            # If we get a response without error, the API key is valid
            return test_response is not None

        except Exception as e:
            self.logger.error(f"API key validation failed: {str(e)}")
            return False

    def get_model_info(self, model: str = None) -> Dict[str, Any]:
        """
        Get information about the model.

        Args:
            model: Model name to get info for (defaults to settings)

        Returns:
            Dict with model information
        """
        if model is None:
            model = settings.LLM_MODEL_NAME

        return {
            "model_name": model,
            "temperature": settings.LLM_TEMPERATURE,
            "max_tokens": settings.LLM_MAX_TOKENS,
            "base_url": settings.LLM_BASE_URL
        }

    async def get_usage_metrics(self) -> Dict[str, Any]:
        """
        Get usage metrics (placeholder - actual metrics may not be available through this interface).

        Returns:
            Dict with usage information
        """
        # Note: Actual usage metrics might not be available through the OpenAI-compatible API
        # This is a placeholder implementation
        return {
            "model_calls": 0,  # This would need to be tracked separately
            "tokens_used": 0,  # This would need to be tracked separately
            "last_call_time": None
        }

    async def health_check(self) -> bool:
        """
        Perform a health check by validating the API key.

        Returns:
            bool: True if the client is healthy, False otherwise
        """
        try:
            return await self.validate_api_key()
        except Exception:
            return False

    def extract_response_text(self, completion: ChatCompletion) -> str:
        """
        Extract the response text from a ChatCompletion object.

        Args:
            completion: The ChatCompletion object from the API

        Returns:
            str: The extracted response text
        """
        if completion.choices and len(completion.choices) > 0:
            return completion.choices[0].message.content or ""
        return ""

    def format_messages(
        self,
        system_message: Optional[str] = None,
        user_message: Optional[str] = None,
        assistant_message: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Helper method to format messages for the API.

        Args:
            system_message: Optional system message
            user_message: User's message
            assistant_message: Optional assistant's previous message

        Returns:
            List of formatted messages
        """
        messages = []

        if system_message:
            messages.append({"role": "system", "content": system_message})

        if assistant_message:
            messages.append({"role": "assistant", "content": assistant_message})

        if user_message:
            messages.append({"role": "user", "content": user_message})

        return messages


class GeminiClientWrapper(OpenAIClientWrapper):
    """
    Specialized wrapper for Gemini API with additional Gemini-specific functionality.
    """

    def __init__(self, config: Optional[OpenAIClientConfig] = None):
        """
        Initialize the Gemini client wrapper.

        Args:
            config: Configuration for the client (uses settings if not provided)
        """
        super().__init__(config)

    def get_supported_models(self) -> List[str]:
        """
        Get list of supported Gemini models (placeholder implementation).

        Returns:
            List of supported model names
        """
        # In a real implementation, this would call the Gemini API to get supported models
        # For now, return commonly available models
        return [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-pro",
            "gemini-1.0-pro"
        ]

    async def generate_with_safety_settings(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        safety_settings: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> ChatCompletion:
        """
        Generate a response with safety settings (Gemini-specific).

        Args:
            messages: List of messages in the conversation
            model: Model name to use
            temperature: Temperature for response randomness
            max_tokens: Maximum tokens in response
            safety_settings: Safety settings to apply
            **kwargs: Additional parameters

        Returns:
            ChatCompletion: The response from the LLM
        """
        if safety_settings is None:
            # Default safety settings - in a real implementation, these would be Gemini-specific
            safety_settings = {
                "harassment": "low",
                "hate": "low",
                "sexuality": "low",
                "danger": "low"
            }

        # Add safety settings to kwargs if the API supports it
        kwargs["extra_headers"] = kwargs.get("extra_headers", {})
        kwargs["extra_headers"]["x-safety-settings"] = str(safety_settings)

        return await self.generate_response(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )


def create_default_gemini_client() -> GeminiClientWrapper:
    """
    Create a default Gemini client wrapper instance.

    Returns:
        GeminiClientWrapper: A new client wrapper instance
    """
    return GeminiClientWrapper()


def create_openai_client_from_settings() -> OpenAIClientWrapper:
    """
    Create an OpenAI client wrapper using the application settings.

    Returns:
        OpenAIClientWrapper: A new client wrapper instance configured with settings
    """
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set in settings")

    config = OpenAIClientConfig(
        api_key=settings.GEMINI_API_KEY,
        base_url=settings.LLM_BASE_URL,
        timeout=30.0,
        max_retries=3
    )

    return OpenAIClientWrapper(config)


if __name__ == "__main__":
    # Example usage
    print("OpenAI Client Wrapper module loaded!")

    # This would typically be used as follows:
    # client = create_openai_client_from_settings()
    # messages = [{"role": "user", "content": "Hello, world!"}]
    # response = await client.generate_response(messages)
    # text = client.extract_response_text(response)
    # print(f"Response: {text}")