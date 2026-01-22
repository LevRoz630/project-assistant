"""AI/LLM service using LangChain."""

from collections.abc import AsyncGenerator

from config import get_settings
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

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


SYSTEM_PROMPT = """You are a helpful personal AI assistant with access to the user's Microsoft 365 data.

CRITICAL RULES:
- ONLY use information explicitly provided in the context below
- NEVER fabricate, invent, or hallucinate data (tasks, emails, events, notes)
- If no data is provided for a category, say "I don't have access to that data" or "No data available"
- If context is empty or says "No relevant notes found", do NOT make up example content

ACTIONS - You can propose actions for the user to approve:
When the user asks you to create, add, or schedule something, output an ACTION block:

For calendar events:
```ACTION
{{"type": "create_event", "subject": "Event title", "start_datetime": "YYYY-MM-DDTHH:MM:SS", "end_datetime": "YYYY-MM-DDTHH:MM:SS", "body": "optional description"}}
```

For tasks:
```ACTION
{{"type": "create_task", "title": "Task title", "body": "optional details", "due_date": "YYYY-MM-DDTHH:MM:SS"}}
```

For notes:
```ACTION
{{"type": "create_note", "folder": "Diary|Projects|Study|Inbox", "filename": "note-name.md", "content": "Note content in markdown"}}
```

Always include a brief explanation before or after the ACTION block. The user will see the proposed action and can approve or reject it.

Current date and time: {current_date}

{context}

{tasks_context}

{calendar_context}

{email_context}
"""


def create_chat_prompt():
    """Create the chat prompt template."""
    return ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
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
) -> str:
    """Generate a response from the AI."""
    llm = get_llm(provider, model)
    prompt = create_chat_prompt()

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
) -> AsyncGenerator[str, None]:
    """Generate a streaming response from the AI."""
    llm = get_llm(provider, model)
    prompt = create_chat_prompt()

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
