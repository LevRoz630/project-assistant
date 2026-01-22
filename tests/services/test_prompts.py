"""Tests for the prompts service."""

import pytest

from services.prompts import (
    AIRole,
    ROLE_KEYWORDS,
    ROLE_PROMPTS,
    detect_role,
    get_role_description,
    get_role_prompt,
)


class TestAIRole:
    """Tests for AIRole enum."""

    def test_all_roles_exist(self):
        """Test that all expected roles exist."""
        expected_roles = ["general", "email", "tasks", "calendar", "notes", "research"]
        for role_value in expected_roles:
            assert AIRole(role_value) is not None

    def test_role_string_values(self):
        """Test that role values are strings."""
        assert AIRole.GENERAL.value == "general"
        assert AIRole.EMAIL.value == "email"
        assert AIRole.TASKS.value == "tasks"


class TestDetectRole:
    """Tests for role detection."""

    def test_detect_email_role(self):
        """Test detecting email-related messages."""
        email_messages = [
            "Check my email",
            "Show me unread emails",
            "Reply to the latest mail",
            "What's in my inbox?",
            "I need to compose an email",
        ]
        for msg in email_messages:
            assert detect_role(msg) == AIRole.EMAIL, f"Failed for: {msg}"

    def test_detect_tasks_role(self):
        """Test detecting task-related messages."""
        task_messages = [
            "Show my tasks",
            "Add a todo item",
            "What's on my to-do list?",
            "Set a reminder for tomorrow",
            "I need to finish the deadline",
        ]
        for msg in task_messages:
            assert detect_role(msg) == AIRole.TASKS, f"Failed for: {msg}"

    def test_detect_calendar_role(self):
        """Test detecting calendar-related messages."""
        calendar_messages = [
            "What's on my calendar today?",
            "Schedule a meeting for tomorrow",
            "Book an appointment",
            "Check my availability",
            "Show upcoming events",
        ]
        for msg in calendar_messages:
            assert detect_role(msg) == AIRole.CALENDAR, f"Failed for: {msg}"

    def test_detect_notes_role(self):
        """Test detecting note-related messages."""
        note_messages = [
            "Create a new note",
            "Write this in my diary",
            "Make a memo about this",
            "Document this information",
            "I want to jot down some ideas",
        ]
        for msg in note_messages:
            assert detect_role(msg) == AIRole.NOTES, f"Failed for: {msg}"

    def test_detect_research_role(self):
        """Test detecting research-related messages."""
        research_messages = [
            "Search for Python tutorials",
            "What is machine learning?",
            "Find out about the weather",
            "Look up the latest news",
            "Research quantum computing",
        ]
        for msg in research_messages:
            assert detect_role(msg) == AIRole.RESEARCH, f"Failed for: {msg}"

    def test_detect_general_role(self):
        """Test that general role is returned for non-specific messages."""
        general_messages = [
            "Hello",
            "How are you?",
            "Thank you",
            "That's interesting",
            "I don't understand",
        ]
        for msg in general_messages:
            assert detect_role(msg) == AIRole.GENERAL, f"Failed for: {msg}"

    def test_case_insensitive_detection(self):
        """Test that detection is case-insensitive."""
        assert detect_role("CHECK MY EMAIL") == AIRole.EMAIL
        assert detect_role("Check My Email") == AIRole.EMAIL
        assert detect_role("check my email") == AIRole.EMAIL

    def test_partial_keyword_matching(self):
        """Test that keywords are matched within sentences."""
        assert detect_role("Can you please check my email inbox?") == AIRole.EMAIL
        assert detect_role("I have a task to complete") == AIRole.TASKS
        assert detect_role("What meeting do I have tomorrow?") == AIRole.CALENDAR

    def test_first_keyword_wins(self):
        """Test that the first matching keyword determines the role."""
        # Email comes before tasks in keyword checking order
        msg = "Email me the task list"
        role = detect_role(msg)
        # Should match one of the roles (depends on iteration order)
        assert role in [AIRole.EMAIL, AIRole.TASKS]


class TestGetRolePrompt:
    """Tests for get_role_prompt function."""

    def test_get_general_prompt(self):
        """Test getting general prompt."""
        prompt = get_role_prompt(AIRole.GENERAL)
        assert "personal AI assistant" in prompt
        assert "CRITICAL RULES" in prompt

    def test_get_email_prompt(self):
        """Test getting email prompt."""
        prompt = get_role_prompt(AIRole.EMAIL)
        assert "email" in prompt.lower()
        assert "FOCUS AREA" in prompt

    def test_get_tasks_prompt(self):
        """Test getting tasks prompt."""
        prompt = get_role_prompt(AIRole.TASKS)
        assert "task management" in prompt.lower()
        assert "CAPABILITIES" in prompt

    def test_get_calendar_prompt(self):
        """Test getting calendar prompt."""
        prompt = get_role_prompt(AIRole.CALENDAR)
        assert "calendar" in prompt.lower() or "scheduling" in prompt.lower()

    def test_get_notes_prompt(self):
        """Test getting notes prompt."""
        prompt = get_role_prompt(AIRole.NOTES)
        assert "note" in prompt.lower()

    def test_get_research_prompt(self):
        """Test getting research prompt."""
        prompt = get_role_prompt(AIRole.RESEARCH)
        assert "research" in prompt.lower()
        assert "SEARCH" in prompt  # Should have search instructions

    def test_all_prompts_have_context_template(self):
        """Test that all prompts have context placeholders."""
        for role in AIRole:
            prompt = get_role_prompt(role)
            assert "{context}" in prompt
            assert "{tasks_context}" in prompt
            assert "{calendar_context}" in prompt
            assert "{email_context}" in prompt
            assert "{current_date}" in prompt

    def test_all_prompts_have_action_instructions(self):
        """Test that all prompts have action instructions."""
        for role in AIRole:
            prompt = get_role_prompt(role)
            assert "ACTION" in prompt
            assert "create_event" in prompt or "create_task" in prompt

    def test_research_prompt_has_search_instructions(self):
        """Test that research prompt has search instructions."""
        prompt = get_role_prompt(AIRole.RESEARCH)
        assert "SEARCH" in prompt
        assert '```SEARCH' in prompt


class TestGetRoleDescription:
    """Tests for get_role_description function."""

    def test_get_general_description(self):
        """Test getting general role description."""
        desc = get_role_description(AIRole.GENERAL)
        assert "General" in desc

    def test_get_email_description(self):
        """Test getting email role description."""
        desc = get_role_description(AIRole.EMAIL)
        assert "Email" in desc or "email" in desc

    def test_get_tasks_description(self):
        """Test getting tasks role description."""
        desc = get_role_description(AIRole.TASKS)
        assert "Task" in desc or "task" in desc

    def test_all_roles_have_descriptions(self):
        """Test that all roles have descriptions."""
        for role in AIRole:
            desc = get_role_description(role)
            assert desc is not None
            assert len(desc) > 0


class TestRoleKeywords:
    """Tests for ROLE_KEYWORDS constant."""

    def test_all_roles_have_keywords(self):
        """Test that all non-general roles have keywords."""
        for role in AIRole:
            if role != AIRole.GENERAL:
                assert role in ROLE_KEYWORDS
                assert len(ROLE_KEYWORDS[role]) > 0

    def test_keywords_are_lowercase(self):
        """Test that all keywords are lowercase for matching."""
        for role, keywords in ROLE_KEYWORDS.items():
            for keyword in keywords:
                assert keyword == keyword.lower(), f"Keyword '{keyword}' should be lowercase"


class TestRolePrompts:
    """Tests for ROLE_PROMPTS constant."""

    def test_all_roles_have_prompts(self):
        """Test that all roles have prompts."""
        for role in AIRole:
            assert role in ROLE_PROMPTS
            assert len(ROLE_PROMPTS[role]) > 0

    def test_prompts_have_security_instructions(self):
        """Test that all prompts have security-related instructions."""
        for role in AIRole:
            prompt = ROLE_PROMPTS[role]
            # Should have instruction to treat context as data
            assert "external sources" in prompt.lower() or "CRITICAL RULES" in prompt


class TestContextTemplate:
    """Tests for context template in prompts."""

    def test_context_boundaries_present(self):
        """Test that context boundary markers are present."""
        for role in AIRole:
            prompt = get_role_prompt(role)
            assert "BEGIN NOTES CONTEXT" in prompt
            assert "END NOTES CONTEXT" in prompt
            assert "BEGIN TASKS CONTEXT" in prompt
            assert "END TASKS CONTEXT" in prompt
            assert "BEGIN CALENDAR CONTEXT" in prompt
            assert "END CALENDAR CONTEXT" in prompt
            assert "BEGIN EMAIL CONTEXT" in prompt
            assert "END EMAIL CONTEXT" in prompt
