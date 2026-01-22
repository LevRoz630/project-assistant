"""AI/LLM service using LangChain."""

from collections.abc import AsyncGenerator

from config import get_settings
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from services.prompts import AIRole, get_role_prompt

settings = get_settings()


def get_llm(provider: str | None = None, model: str | None = None):
    """Get the LLM instance based on provider."""
    provider = provider or settings.default_llm_provider
    model = model or settings.default_model

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
