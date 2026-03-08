"""AI/LLM service using LangChain."""

from collections.abc import AsyncGenerator

from ..config import get_settings
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from .prompts import AIRole, get_role_prompt

settings = get_settings()


_PROVIDER_KEYS = {
    "anthropic": "anthropic_api_key",
    "openai": "openai_api_key",
    "google": "google_api_key",
}

_DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4o",
    "google": "gemini-2.0-flash",
}


def _resolve_provider(provider: str | None) -> str:
    """Resolve the LLM provider, falling back to whichever has a key configured."""
    requested = provider or settings.default_llm_provider
    # If the requested provider has a key, use it
    if getattr(settings, _PROVIDER_KEYS.get(requested, ""), ""):
        return requested
    # Otherwise, find the first provider that has a key
    for name, key_attr in _PROVIDER_KEYS.items():
        if getattr(settings, key_attr, ""):
            return name
    raise ValueError(
        "No LLM API key configured. Set one of: "
        "ANTHROPIC_API_KEY, OPENAI_API_KEY, or GOOGLE_API_KEY"
    )


def get_llm(provider: str | None = None, model: str | None = None):
    """Get the LLM instance based on provider."""
    provider = _resolve_provider(provider)
    model = model or _DEFAULT_MODELS.get(provider, settings.default_model)

    if provider == "anthropic":
        return ChatAnthropic(
            model=model,
            api_key=settings.anthropic_api_key,
            max_tokens=4096,
        )
    elif provider == "openai":
        return ChatOpenAI(
            model=model,
            api_key=settings.openai_api_key,
        )
    elif provider == "google":
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=settings.google_api_key,
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")


def create_chat_prompt(system_prompt: str):
    """Create the chat prompt template with the given system prompt."""
    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
        ]
    )


async def generate_response(
    user_input: str,
    context: str = "",
    tasks_context: str = "",
    calendar_context: str = "",
    email_context: str = "",
    chat_history: list | None = None,
    current_date: str = "",
    provider: str | None = None,
    model: str | None = None,
    role: AIRole | None = None,
) -> str:
    """Generate a response from the AI.

    Args:
        user_input: The user's message
        context: Notes/RAG context
        tasks_context: Tasks context
        calendar_context: Calendar context
        email_context: Email context
        chat_history: Previous conversation messages
        current_date: Current date string
        provider: LLM provider (anthropic/openai)
        model: Model name
        role: AI role for specialized prompts (auto-detected if None)

    Returns:
        The AI response string
    """
    llm = get_llm(provider, model)

    # Get role-specific prompt
    effective_role = role or AIRole.GENERAL
    system_prompt = get_role_prompt(effective_role)
    prompt = create_chat_prompt(system_prompt)

    chain = prompt | llm

    # Convert chat history to messages
    history_messages = []
    if chat_history:
        for msg in chat_history:
            if msg["role"] == "user":
                history_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                history_messages.append(AIMessage(content=msg["content"]))

    response = await chain.ainvoke(
        {
            "input": user_input,
            "context": f"Context from notes:\n{context}" if context else "No relevant notes found.",
            "tasks_context": f"Your tasks:\n{tasks_context}" if tasks_context else "",
            "calendar_context": f"Your calendar:\n{calendar_context}" if calendar_context else "",
            "email_context": f"Recent emails:\n{email_context}" if email_context else "",
            "chat_history": history_messages,
            "current_date": current_date,
        }
    )

    return response.content


async def generate_response_stream(
    user_input: str,
    context: str = "",
    tasks_context: str = "",
    calendar_context: str = "",
    email_context: str = "",
    chat_history: list | None = None,
    current_date: str = "",
    provider: str | None = None,
    model: str | None = None,
    role: AIRole | None = None,
) -> AsyncGenerator[str, None]:
    """Generate a streaming response from the AI.

    Args:
        user_input: The user's message
        context: Notes/RAG context
        tasks_context: Tasks context
        calendar_context: Calendar context
        email_context: Email context
        chat_history: Previous conversation messages
        current_date: Current date string
        provider: LLM provider (anthropic/openai)
        model: Model name
        role: AI role for specialized prompts (auto-detected if None)

    Yields:
        Chunks of the AI response
    """
    llm = get_llm(provider, model)

    # Get role-specific prompt
    effective_role = role or AIRole.GENERAL
    system_prompt = get_role_prompt(effective_role)
    prompt = create_chat_prompt(system_prompt)

    chain = prompt | llm

    # Convert chat history to messages
    history_messages = []
    if chat_history:
        for msg in chat_history:
            if msg["role"] == "user":
                history_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                history_messages.append(AIMessage(content=msg["content"]))

    async for chunk in chain.astream(
        {
            "input": user_input,
            "context": f"Context from notes:\n{context}" if context else "No relevant notes found.",
            "tasks_context": f"Your tasks:\n{tasks_context}" if tasks_context else "",
            "calendar_context": f"Your calendar:\n{calendar_context}" if calendar_context else "",
            "email_context": f"Recent emails:\n{email_context}" if email_context else "",
            "chat_history": history_messages,
            "current_date": current_date,
        }
    ):
        if hasattr(chunk, "content"):
            yield chunk.content
