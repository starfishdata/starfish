import pytest
from starfish.common.prompt import PromptManager

class TestJinjaPromptManager:
    """Test cases for the JinjaPromptManager class."""
    
    def test_basic_required_variables(self):
        """Test identifying required variables in a basic template."""
        template = "Hello, {{ name }}! Your age is {{ age }}."
        manager = PromptManager(template)
        
        # Check variable identification
        assert set(manager.get_all_variables()) == {"name", "age"}
        assert set(manager.get_required_variables()) == {"name", "age"}
        assert manager.get_optional_variables() == []
        
        # Test rendering with all variables
        result = manager.render_template({"name": "Alice", "age": 30})
        assert result == "Hello, Alice! Your age is 30."
    
    def test_conditional_variables(self):
        """Test identifying optional variables in conditional blocks."""
        template = """
        Hello, {{ name }}!
        {% if show_age %}
        Your age is {{ age }}.
        {% endif %}
        """
        manager = PromptManager(template)
        
        # Check variable identification
        assert set(manager.get_all_variables()) == {"name", "show_age", "age"}
        assert set(manager.get_required_variables()) == {"name"}
        assert set(manager.get_optional_variables()) == {"show_age", "age"}
        
        # Test rendering with all variables
        result = manager.render_template({
            "name": "Bob", 
            "show_age": True, 
            "age": 25
        }).strip()
        assert "Hello, Bob!" in result
        assert "Your age is 25." in result
        
        # Test rendering with only required variables
        result = manager.render_template({
            "name": "Charlie", 
            "show_age": False
        }).strip()
        assert "Hello, Charlie!" in result
        assert "Your age is" not in result
    
    def test_nested_conditional_variables(self):
        """Test identifying optional variables in nested conditional blocks."""
        template = """
        Hello, {{ name }}!
        {% if show_details %}
            {% if show_age %}
            Your age is {{ age }}.
            {% endif %}
            {% if show_location %}
            Your location is {{ location }}.
            {% endif %}
        {% endif %}
        """
        manager = PromptManager(template)
        
        # Check variable identification
        all_vars = set(manager.get_all_variables())
        required_vars = set(manager.get_required_variables())
        optional_vars = set(manager.get_optional_variables())
        
        assert all_vars == {"name", "show_details", "show_age", "age", "show_location", "location"}
        assert required_vars == {"name"}
        assert optional_vars == {"show_details", "show_age", "age", "show_location", "location"}
        
        # Test rendering with all variables
        result = manager.render_template({
            "name": "Dave",
            "show_details": True,
            "show_age": True,
            "age": 30,
            "show_location": True,
            "location": "New York"
        }).strip()
        
        assert "Hello, Dave!" in result
        assert "Your age is 30." in result
        assert "Your location is New York." in result
        
        # Test rendering with only some optional variables
        result = manager.render_template({
            "name": "Eve",
            "show_details": True,
            "show_age": False,
            "show_location": True,
            "location": "London"
        }).strip()
        
        assert "Hello, Eve!" in result
        assert "Your age is" not in result
        assert "Your location is London." in result
        
        # Test rendering with top-level conditional False
        result = manager.render_template({
            "name": "Frank",
            "show_details": False
        }).strip()
        
        assert "Hello, Frank!" in result
        assert "Your age is" not in result
        assert "Your location is" not in result
    
    def test_mixed_variables(self):
        """Test variables used in both conditional and non-conditional contexts."""
        template = """
        Hello, {{ name }}!
        
        {% if show_details %}
        Your details: {{ details }}
        {% endif %}
        
        Always show: {{ details }}
        """
        manager = PromptManager(template)
        
        # Check variable identification
        assert set(manager.get_all_variables()) == {"name", "show_details", "details"}
        assert set(manager.get_required_variables()) == {"name", "details"}
        assert set(manager.get_optional_variables()) == {"show_details"}
        
        # Test rendering with all variables
        result = manager.render_template({
            "name": "George", 
            "show_details": True,
            "details": "Some details"
        }).strip()
        
        assert "Hello, George!" in result
        assert "Your details: Some details" in result
        assert "Always show: Some details" in result
    
    def test_conditional_in_conditional(self):
        """Test variables that are conditional on other conditionals."""
        template = """
        Hello, {{ name }}!
        
        {% if show_details %}
            {% if details %}
            Your details: {{ details }}
            {% endif %}
        {% endif %}
        """
        manager = PromptManager(template)
        
        # Check variable identification
        assert set(manager.get_all_variables()) == {"name", "show_details", "details"}
        assert set(manager.get_required_variables()) == {"name"}
        assert set(manager.get_optional_variables()) == {"show_details", "details"}
    
    def test_error_on_missing_required(self):
        """Test error handling for missing required variables."""
        template = "Hello, {{ name }}! Your favorite color is {{ color }}."
        manager = PromptManager(template)
        
        # Should raise ValueError due to missing 'color'
        with pytest.raises(ValueError) as exc_info:
            manager.render_template({"name": "Helen"})
        
        assert "Required variable 'color' is missing" in str(exc_info.value)
    
    def test_error_on_none_required(self):
        """Test error handling for None values in required variables."""
        template = "Hello, {{ name }}! Your favorite color is {{ color }}."
        manager = PromptManager(template)
        
        # Should raise ValueError due to None value for 'color'
        with pytest.raises(ValueError) as exc_info:
            manager.render_template({"name": "Ivan", "color": None})
        
        assert "Required variable 'color' cannot be None" in str(exc_info.value)
    
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
        
        # Check variable identification
        all_vars = set(manager.get_all_variables())
        req_vars = set(manager.get_required_variables())
        opt_vars = set(manager.get_optional_variables())
        
        expected_all = {"condition1", "var1", "nested_condition", "var2", "var3", 
                        "condition2", "var4", "var5", "standalone_condition", "var6"}
        expected_req = {"var1"}
        expected_opt = {"condition1", "nested_condition", "var2", "var3", 
                        "condition2", "var4", "var5", "standalone_condition", "var6"}
        
        assert all_vars == expected_all
        assert req_vars == expected_req
        assert opt_vars == expected_opt 

    

def test_complex_templates():
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
    
    # Check variable identification
    all_vars = set(manager.get_all_variables())
    req_vars = set(manager.get_required_variables())
    opt_vars = set(manager.get_optional_variables())
    
    expected_all = {"condition1", "var1", "nested_condition", "var2", "var3", 
                    "condition2", "var4", "var5", "standalone_condition", "var6"}
    expected_req = {"var1"}
    expected_opt = {"condition1", "nested_condition", "var2", "var3", 
                    "condition2", "var4", "var5", "standalone_condition", "var6"}
    
    assert all_vars == expected_all
    assert req_vars == expected_req
    assert opt_vars == expected_opt 