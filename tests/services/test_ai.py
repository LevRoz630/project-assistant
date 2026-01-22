"""Tests for the AI service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestGetLLM:
    """Tests for get_llm function."""

    def test_get_llm_anthropic(self):
        """Test getting Anthropic LLM."""
        with patch("services.ai.ChatAnthropic") as mock_anthropic:
            from services.ai import get_llm

            get_llm(provider="anthropic", model="claude-sonnet-4-20250514")

            mock_anthropic.assert_called_once()
            call_kwargs = mock_anthropic.call_args.kwargs
            assert call_kwargs["model"] == "claude-sonnet-4-20250514"

    def test_get_llm_openai(self):
        """Test getting OpenAI LLM."""
        with patch("services.ai.ChatOpenAI") as mock_openai:
            from services.ai import get_llm

            get_llm(provider="openai", model="gpt-4")

            mock_openai.assert_called_once()
            call_kwargs = mock_openai.call_args.kwargs
            assert call_kwargs["model"] == "gpt-4"

    def test_get_llm_default_provider(self):
        """Test getting LLM with default provider."""
        with patch("services.ai.ChatAnthropic") as mock_anthropic:
            with patch("services.ai.settings") as mock_settings:
                mock_settings.default_llm_provider = "anthropic"
                mock_settings.default_model = "claude-sonnet-4-20250514"
                mock_settings.anthropic_api_key = "test-key"

                from services.ai import get_llm

                get_llm()
                mock_anthropic.assert_called()

    def test_get_llm_invalid_provider(self):
        """Test getting LLM with invalid provider raises error."""
        from services.ai import get_llm

        with pytest.raises(ValueError, match="Unknown provider"):
            get_llm(provider="invalid_provider")


class TestCreateChatPrompt:
    """Tests for create_chat_prompt function."""

    def test_create_chat_prompt(self):
        """Test creating chat prompt template."""
        from services.ai import create_chat_prompt

        prompt = create_chat_prompt()

        assert prompt is not None
        # Check that it has the expected input variables
        assert "input" in str(prompt.messages)


class TestGenerateResponse:
    """Tests for generate_response function."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM."""
        mock = MagicMock()
        mock.ainvoke = AsyncMock(return_value=MagicMock(content="AI response here"))
        return mock

    @pytest.mark.asyncio
    async def test_generate_response_basic(self, mock_llm):
        """Test basic response generation."""
        with patch("services.ai.get_llm", return_value=mock_llm):
            from services.ai import generate_response

            response = await generate_response(
                user_input="Hello, how are you?",
                current_date="2024-01-15 10:00",
            )

            assert response == "AI response here"
            mock_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_response_with_context(self, mock_llm):
        """Test response generation with context."""
        with patch("services.ai.get_llm", return_value=mock_llm):
            from services.ai import generate_response

            response = await generate_response(
                user_input="What did I write yesterday?",
                context="Yesterday's diary entry: Worked on project.",
                current_date="2024-01-15 10:00",
            )

            assert response == "AI response here"
            # Verify context was passed
            call_args = mock_llm.ainvoke.call_args
            assert "Context from notes" in str(call_args)

    @pytest.mark.asyncio
    async def test_generate_response_with_tasks_context(self, mock_llm):
        """Test response generation with tasks context."""
        with patch("services.ai.get_llm", return_value=mock_llm):
            from services.ai import generate_response

            response = await generate_response(
                user_input="What tasks do I have?",
                tasks_context="- [notStarted] Buy groceries",
                current_date="2024-01-15 10:00",
            )

            assert response == "AI response here"
            call_args = mock_llm.ainvoke.call_args
            assert "Your tasks" in str(call_args)

    @pytest.mark.asyncio
    async def test_generate_response_with_calendar_context(self, mock_llm):
        """Test response generation with calendar context."""
        with patch("services.ai.get_llm", return_value=mock_llm):
            from services.ai import generate_response

            response = await generate_response(
                user_input="What meetings do I have today?",
                calendar_context="- 10:00: Team Meeting @ Room 101",
                current_date="2024-01-15 10:00",
            )

            assert response == "AI response here"
            call_args = mock_llm.ainvoke.call_args
            assert "Your calendar" in str(call_args)

    @pytest.mark.asyncio
    async def test_generate_response_with_chat_history(self, mock_llm):
        """Test response generation with chat history."""
        with patch("services.ai.get_llm", return_value=mock_llm):
            from services.ai import generate_response

            history = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ]

            response = await generate_response(
                user_input="How are you?",
                chat_history=history,
                current_date="2024-01-15 10:00",
            )

            assert response == "AI response here"


class TestGenerateResponseStream:
    """Tests for generate_response_stream function."""

    @pytest.fixture
    def mock_streaming_llm(self):
        """Create mock streaming LLM."""
        mock = MagicMock()

        async def mock_astream(*args, **kwargs):
            chunks = [
                MagicMock(content="Hello"),
                MagicMock(content=" there"),
                MagicMock(content="!"),
            ]
            for chunk in chunks:
                yield chunk

        mock.astream = mock_astream
        return mock

    @pytest.mark.asyncio
    async def test_generate_response_stream(self, mock_streaming_llm):
        """Test streaming response generation."""
        with patch("services.ai.get_llm", return_value=mock_streaming_llm):
            from services.ai import generate_response_stream

            chunks = []
            async for chunk in generate_response_stream(
                user_input="Hello",
                current_date="2024-01-15 10:00",
            ):
                chunks.append(chunk)

            assert len(chunks) == 3
            assert "".join(chunks) == "Hello there!"

    @pytest.mark.asyncio
    async def test_generate_response_stream_with_context(self, mock_streaming_llm):
        """Test streaming with context."""
        with patch("services.ai.get_llm", return_value=mock_streaming_llm):
            from services.ai import generate_response_stream

            chunks = []
            async for chunk in generate_response_stream(
                user_input="Question?",
                context="Some context",
                tasks_context="Tasks here",
                calendar_context="Calendar here",
                current_date="2024-01-15 10:00",
            ):
                chunks.append(chunk)

            assert len(chunks) == 3


class TestSystemPrompt:
    """Tests for system prompt configuration."""

    def test_system_prompt_contains_required_sections(self):
        """Test that system prompt has required sections."""
        from services.ai import SYSTEM_PROMPT

        assert "notes" in SYSTEM_PROMPT.lower()
        assert "tasks" in SYSTEM_PROMPT.lower()
        assert "calendar" in SYSTEM_PROMPT.lower()
        assert "{context}" in SYSTEM_PROMPT
        assert "{tasks_context}" in SYSTEM_PROMPT
        assert "{calendar_context}" in SYSTEM_PROMPT
        assert "{current_date}" in SYSTEM_PROMPT
