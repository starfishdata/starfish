import pytest

from starfish.llm.prompt import PromptManager
from starfish.llm.prompt.prompt_loader import get_partial_prompt, get_prompt

"""Tests for the PromptManager class and related functionality in starfish.llm.prompt.

This test suite covers:
1. Variable identification (required vs optional variables in templates)
2. Template rendering with different variable combinations
3. Error handling for missing or invalid variables
4. Special features like list input detection, num_records handling
5. Utility methods like get_prompt and get_partial_prompt

Note: Although the PromptManager appends a MANDATE_INSTRUCTION that contains
schema_instruction and other variables, it does not treat schema_instruction
as a required variable. The test cases follow the actual implementation behavior
which identifies only variables used outside of conditional blocks in the
original user template as "required".
"""


# Utility functions for test setup
def get_expected_mandate_vars(required=False):
    """Get the list of variables added by MANDATE_INSTRUCTION.

    Args:
        required: If True, return only variables that would be classified as required.
                 If False (default), return only variables that would be classified as optional.

    Returns:
        Set of variable names.
    """
    all_mandate_vars = {"is_list_input", "list_input_variable", "input_list_length", "schema_instruction", "num_records"}

    # In practice, none of the mandate variables are treated as required
    if required:
        return set()
    else:
        return all_mandate_vars


# Fixtures
@pytest.fixture
def basic_template():
    """Simple template with basic variables for testing."""
    return "Hello, {{ name }}! Your age is {{ age }}."


@pytest.fixture
def simple_prompt_manager(basic_template):
    """Basic PromptManager instance with a simple template."""
    return PromptManager(basic_template)


@pytest.fixture
def standard_variables():
    """Common variables used in multiple tests."""
    return {"name": "Alice", "age": 30, "schema_instruction": "Test schema"}


class TestPromptManager:
    """Test cases for the PromptManager class."""

    # ---------------------------------------------------------------------------
    # Tests for variable identification
    # ---------------------------------------------------------------------------

    def test_basic_required_variables(self, simple_prompt_manager, standard_variables):
        """Test identifying required variables in a basic template."""
        # Note: MANDATE_INSTRUCTION is automatically appended by PromptManager
        manager = simple_prompt_manager

        # Basic variables from template
        expected_template_required = {"name", "age"}
        expected_template_optional = set()

        # Get expected variables including those from MANDATE_INSTRUCTION
        expected_required = expected_template_required.union(get_expected_mandate_vars(required=True))
        expected_optional = expected_template_optional.union(get_expected_mandate_vars(required=False))
        expected_all = expected_required.union(expected_optional)

        # Check variable identification
        assert set(manager.get_all_variables()) == expected_all
        assert set(manager.get_required_variables()) == expected_required
        assert set(manager.get_optional_variables()) == expected_optional

        # Test rendering - requires schema_instruction now
        result = manager.render_template(standard_variables)
        assert "Hello, Alice! Your age is 30." in result
        # Check that part of the non-list mandate instruction is present
        assert "You are asked to generate exactly 1 records" in result
        assert "Test schema" in result

    @pytest.mark.parametrize(
        "template,template_required,template_optional,test_name",
        [
            # Basic conditional test
            (
                """
            Hello, {{ name }}!
            {% if show_age %}
            Your age is {{ age }}.
            {% endif %}
            """,
                {"name"},
                {"show_age", "age"},
                "basic_conditional",
            ),
            # Nested conditional test
            (
                """
            Hello, {{ name }}!
            {% if show_details %}
                {% if show_age %}
                Your age is {{ age }}.
                {% endif %}
                {% if show_location %}
                Your location is {{ location }}.
                {% endif %}
            {% endif %}
            """,
                {"name"},
                {"show_details", "show_age", "age", "show_location", "location"},
                "nested_conditional",
            ),
            # Mixed conditional test
            (
                """
            Hello, {{ name }}!

            {% if show_details %}
            Your details: {{ details }}
            {% endif %}

            Always show: {{ details }}
            """,
                {"name", "details"},
                {"show_details"},
                "mixed_variables",
            ),
            # Conditional in conditional test
            (
                """
            Hello, {{ name }}!

            {% if show_details %}
                {% if details %}
                Your details: {{ details }}
                {% endif %}
            {% endif %}
            """,
                {"name"},
                {"show_details", "details"},
                "conditional_in_conditional",
            ),
        ],
    )
    def test_conditional_variable_analysis(self, template, template_required, template_optional, test_name):
        """Test variable analysis with various conditional structures."""
        manager = PromptManager(template)

        # Get the variables
        all_vars = set(manager.get_all_variables())
        required_vars = set(manager.get_required_variables())
        optional_vars = set(manager.get_optional_variables())

        # Get expected variables including those from MANDATE_INSTRUCTION
        expected_required = template_required.union(get_expected_mandate_vars(required=True))
        expected_optional = template_optional.union(get_expected_mandate_vars(required=False))
        expected_all = expected_required.union(expected_optional)

        # Check variable identification
        assert all_vars == expected_all, f"Failed for {test_name}: all variables"
        assert required_vars == expected_required, f"Failed for {test_name}: required variables"
        assert optional_vars == expected_optional, f"Failed for {test_name}: optional variables"

        # Basic rendering test
        if test_name == "basic_conditional":
            # Test showing age
            result = manager.render_template({"name": "Bob", "show_age": True, "age": 25, "schema_instruction": "Age schema"}).strip()
            assert "Hello, Bob!" in result
            assert "Your age is 25." in result

            # Test hiding age
            result = manager.render_template({"name": "Charlie", "show_age": False, "schema_instruction": "No age schema"}).strip()
            assert "Hello, Charlie!" in result
            assert "Your age is" not in result

    def test_complex_templates(self):
        """Test more complex template structures."""
        template = """
        {% if condition1 %}
            {{ var1 }} is shown in condition1
            {% if nested_condition %}
                {{ var2 }} is in nested condition
                {{ var3 }} is also in nested condition
            {% endif %}
        {% elif condition2 %}
            {{ var1 }} is shown in condition2
            {{ var4 }} is only in condition2
        {% else %}
            {{ var1 }} is shown in else block
            {{ var5 }} is only in else block
        {% endif %}

        {{ var1 }} appears outside all conditions
        {% if standalone_condition %}
            {{ var6 }} is in a different conditional
        {% endif %}
        """

        manager = PromptManager(template)

        # Template variables
        template_required = {"var1"}
        template_optional = {"condition1", "nested_condition", "var2", "var3", "condition2", "var4", "var5", "standalone_condition", "var6"}

        # Get expected variables including those from MANDATE_INSTRUCTION
        expected_req = template_required.union(get_expected_mandate_vars(required=True))
        expected_opt = template_optional.union(get_expected_mandate_vars(required=False))
        expected_all = expected_req.union(expected_opt)

        # Check variable identification
        all_vars = set(manager.get_all_variables())
        req_vars = set(manager.get_required_variables())
        opt_vars = set(manager.get_optional_variables())

        assert all_vars == expected_all
        assert req_vars == expected_req
        assert opt_vars == expected_opt

        # Add a basic render test for completeness
        result = manager.render_template(
            {"var1": "Value1", "schema_instruction": "Complex Schema", "condition1": False, "condition2": False, "standalone_condition": False}
        ).strip()
        assert "Value1 is shown in else block" in result
        assert "Value1 appears outside all conditions" in result
        assert "is in a different conditional" not in result
        assert "You are asked to generate exactly 1 records" in result
        assert "Complex Schema" in result

    # ---------------------------------------------------------------------------
    # Tests for error handling
    # ---------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "missing_var,variables,error_message",
        [
            # Missing required variables
            ("color", {"name": "Helen", "schema_instruction": "Schema"}, "Required variable 'color' is missing"),
            ("name", {"color": "Blue", "schema_instruction": "Schema"}, "Required variable 'name' is missing"),
            # None values for required variables
            ("color", {"name": "Ivan", "color": None, "schema_instruction": "Schema"}, "Required variable 'color' cannot be None"),
            ("name", {"name": None, "color": "Green", "schema_instruction": "Schema"}, "Required variable 'name' cannot be None"),
        ],
    )
    def test_error_handling(self, missing_var, variables, error_message):
        """Test error handling for missing or None required variables."""
        template = "Hello, {{ name }}! Your favorite color is {{ color }}."
        manager = PromptManager(template)

        with pytest.raises(ValueError) as exc_info:
            manager.render_template(variables)

        assert error_message in str(exc_info.value)

    # ---------------------------------------------------------------------------
    # Tests for template rendering
    # ---------------------------------------------------------------------------

    def test_list_input_rendering(self):
        """Test rendering when a list is provided as input."""
        template = "Processing items: {{ items_to_process }}"
        manager = PromptManager(template)

        items = ["apple", "banana"]
        result = manager.render_template({"items_to_process": items, "schema_instruction": "List schema"})

        # Check original template part
        # Note: The list itself is replaced by a reference and JSON dump
        assert 'Processing items: |items_to_process| : ["apple", "banana"]' in result

        # Check mandate instruction part for lists
        assert "You are provided with a list named |items_to_process|" in result
        assert "contains exactly 2 elements." in result
        assert "Generate and return a JSON array containing exactly 2 results" in result
        assert "List schema" in result

        # Check mandate instruction part for non-lists is NOT present
        assert "You are asked to generate exactly" not in result

    def test_num_records_rendering(self):
        """Test default and custom num_records rendering."""
        template = "Generate data for {{ topic }}."
        manager = PromptManager(template)

        # Test default num_records = 1
        result_default = manager.render_template({"topic": "Weather", "schema_instruction": "Weather schema"})
        assert "You are asked to generate exactly 1 records" in result_default

        # Test custom num_records = 5
        result_custom = manager.render_template({"topic": "Cities", "schema_instruction": "City schema", "num_records": 5})
        assert "You are asked to generate exactly 5 records" in result_custom

    def test_header_footer_rendering(self):
        """Test rendering with header and footer."""
        template = "This is the main content."
        header = "Header Info"
        footer = "Footer Info"
        manager = PromptManager(template, header=header, footer=footer)

        result = manager.render_template({"schema_instruction": "Header/Footer schema"})

        # Check that header, template, footer are all present
        assert header in result
        assert template in result
        assert footer in result

        # Ensure correct order - header comes before template, template before footer
        assert result.index(header) < result.index(template)
        assert result.index(template) < result.index(footer)

        # Verify schema instruction is included
        assert "Header/Footer schema" in result

    # ---------------------------------------------------------------------------
    # Tests for utility methods
    # ---------------------------------------------------------------------------

    def test_from_string_constructor(self):
        """Test the from_string class method."""
        template = "Test template: {{ var }}"
        manager = PromptManager.from_string(template)
        assert isinstance(manager, PromptManager)
        assert set(manager.get_required_variables()) == {"var"}  # schema_instruction is not treated as required

    def test_construct_messages(self):
        """Test the construct_messages method format."""
        template = "User query: {{ query }}"
        manager = PromptManager(template)
        variables = {"query": "How does this work?", "schema_instruction": "Query schema"}
        messages = manager.construct_messages(variables)

        assert isinstance(messages, list)
        assert len(messages) == 1
        assert isinstance(messages[0], dict)
        assert messages[0]["role"] == "user"
        assert "User query: How does this work?" in messages[0]["content"]
        assert "Query schema" in messages[0]["content"]  # Mandate part

    def test_get_printable_messages(self):
        """Test the get_printable_messages formatting."""
        manager = PromptManager("")  # Empty template, just mandate
        messages = [{"role": "user", "content": "Test content line 1\nTest content line 2"}, {"role": "assistant", "content": "Assistant response"}]
        formatted_string = manager.get_printable_messages(messages)

        assert "========" in formatted_string
        assert "CONSTRUCTED MESSAGES:" in formatted_string
        assert "Role: user" in formatted_string
        assert "Content:\nTest content line 1\nTest content line 2" in formatted_string
        assert "Role: assistant" in formatted_string
        assert "Content:\nAssistant response" in formatted_string
        assert "End of prompt" in formatted_string


# Test the utility functions outside the class
def test_get_prompt():
    """Test the get_prompt utility function."""
    from starfish.llm.prompt.prompt_template import COMPLETE_PROMPTS

    # Get a key from COMPLETE_PROMPTS
    prompt_name = next(iter(COMPLETE_PROMPTS.keys()))

    # Test retrieving a valid prompt
    prompt = get_prompt(prompt_name)
    assert prompt is not None

    # Test cache works (call again)
    prompt_again = get_prompt(prompt_name)
    assert prompt is prompt_again  # Should be the same object (cached)

    # Test invalid prompt name
    with pytest.raises(ValueError) as exc_info:
        get_prompt("nonexistent_prompt_name")

    assert "Unknown complete prompt" in str(exc_info.value)
    assert prompt_name in str(exc_info.value)  # Should list available options


def test_get_partial_prompt():
    """Test the get_partial_prompt utility function."""
    from starfish.llm.prompt.prompt_template import PARTIAL_PROMPTS

    # Get a key from PARTIAL_PROMPTS
    prompt_name = next(iter(PARTIAL_PROMPTS.keys()))

    # Test retrieving a valid partial prompt
    template_str = "Custom template: {{ var }}"
    prompt_manager = get_partial_prompt(prompt_name, template_str)

    assert isinstance(prompt_manager, PromptManager)
    assert "var" in prompt_manager.get_all_variables()

    # Test invalid prompt name
    with pytest.raises(ValueError) as exc_info:
        get_partial_prompt("nonexistent_prompt_name", template_str)

    assert "Unknown partial prompt" in str(exc_info.value)
    assert prompt_name in str(exc_info.value)  # Should list available options
