import functools
import json
import re
from typing import Any, Dict, List, Set, Tuple

from jinja2 import Environment, StrictUndefined, meta, nodes

from starfish.llm.prompt.prompt_template import COMPLETE_PROMPTS, PARTIAL_PROMPTS


class PromptManager:
    """Manages Jinja2 template processing with variable analysis and rendering."""

    MANDATE_INSTRUCTION = """
{% if is_list_input %}
Additional Instructions:

You are provided with a list named |{{ list_input_variable }}| that contains exactly {{ input_list_length }} elements.

Processing:

1. Process each element according to the provided instructions.
2. Generate and return a JSON array containing exactly {{ input_list_length }} results, preserving the original order.
3. Your output must strictly adhere to the following JSON schema:
{{ schema_instruction }}

{% else %}
You are asked to generate exactly {{ num_records }} records and please return the data in the following JSON format:
{{ schema_instruction }}
{% endif %}
"""

    def __init__(self, template_str: str, header: str = "", footer: str = ""):
        """Initialize with template string and analyze variables immediately."""
        # Convert f-string format to Jinja2 if needed
        template_str = self._convert_to_jinja_format(template_str)

        self.template_full = f"{header}\n{template_str}\n{footer}".strip() + f"\n{self.MANDATE_INSTRUCTION}"
        self._env = Environment(undefined=StrictUndefined)
        self._template = self._env.from_string(self.template_full)
        self._ast = self._env.parse(self.template_full)

        # Analyze variables immediately to avoid repeated processing
        self.all_vars, self.required_vars, self.optional_vars = self._analyze_variables()

    @staticmethod
    def _convert_to_jinja_format(template_str: str) -> str:
        """
        Convert Python f-string or string with single braces to Jinja2 template syntax.

        This method safely detects and converts Python-style interpolation with single braces
        to Jinja2 double-brace format, while preserving:

        1. Existing Jinja2 syntax (double braces, control structures, comments)
        2. JSON/dict literals with braces and quotes
        3. Other valid uses of single braces that aren't meant for interpolation

        Known limitations:
        - Complex expressions with string literals inside braces may not be converted properly
        - Triple braces ({{{var}}}) will cause Jinja syntax errors
        - Whitespace inside braces is normalized in the conversion process

        Returns:
            str: A string properly formatted for Jinja2
        """
        if not template_str.strip():
            return template_str

        # If template already contains Jinja2 control structures or comments, preserve it
        if re.search(r"{%.*?%}|{#.*?#}", template_str):
            return template_str

        # If the template already contains Jinja2 variable syntax ({{ }}), preserve it
        if "{{" in template_str and "}}" in template_str:
            return template_str

        # Process the string character by character to handle complex cases
        result = []
        i = 0
        while i < len(template_str):
            # Look for potential variable interpolation pattern {var}
            if template_str[i] == "{" and i + 1 < len(template_str):
                # Skip if it looks like it might be a JSON/dict literal with quotes following
                if i + 1 < len(template_str) and template_str[i + 1] in "\"'":
                    result.append(template_str[i])
                    i += 1
                    continue

                # Skip if it's the start of an escaped brace like {{
                if i + 1 < len(template_str) and template_str[i + 1] == "{":
                    result.append(template_str[i])
                    i += 1
                    continue

                # Try to find the matching closing brace
                j = i + 1
                brace_depth = 1
                has_quotes = False

                while j < len(template_str) and brace_depth > 0:
                    # Track quotes inside the braces
                    if template_str[j] in "\"'" and (j == 0 or template_str[j - 1] != "\\"):
                        has_quotes = True

                    if template_str[j] == "{":
                        brace_depth += 1
                    elif template_str[j] == "}":
                        brace_depth -= 1
                    j += 1

                # Found a matching closing brace
                if brace_depth == 0 and j - i > 2:  # Must have at least one char between braces
                    # Extract the variable expression inside the braces
                    var_content = template_str[i + 1 : j - 1].strip()

                    # Skip conversion for empty braces or very short content
                    if not var_content:
                        result.append(template_str[i:j])
                        i = j
                        continue

                    # Skip complex expressions with quotes for safety
                    if has_quotes and ('"' in var_content or "'" in var_content):
                        result.append(template_str[i:j])
                        i = j
                        continue

                    # Only convert if it looks like a valid variable name or expression
                    # This pattern matches most variable names, attributes, indexing, and operators
                    # but avoids converting things that look like JSON objects
                    if re.match(r"^[a-zA-Z0-9_\.\[\]\(\)\+\-\*\/\|\s\%\<\>\=\!\&]+$", var_content):
                        result.append("{{ ")
                        result.append(var_content)
                        result.append(" }}")
                        i = j
                        continue

                    # If we get here, it's an expression we're unsure about - preserve it
                    result.append(template_str[i:j])
                    i = j
                    continue

            # No special case, add the current character
            result.append(template_str[i])
            i += 1

        return "".join(result)

    @classmethod
    def from_string(cls, template_str: str, header: str = "", footer: str = "") -> "PromptManager":
        """Create from template string."""
        return cls(template_str, header, footer)

    def get_all_variables(self) -> List[str]:
        """Return all variables in the template."""
        return list(self.all_vars)

    def get_prompt(self) -> List[str]:
        """Return all variables in the template."""
        return self.template_full

    def _analyze_variables(self) -> Tuple[Set[str], Set[str], Set[str]]:
        """Analyze variables to identify required vs optional.

        Returns:
            Tuple containing (all_vars, required_vars, optional_vars)
        """
        # Track all variables by context
        root_vars = set()  # Variables used at root level (required)
        conditional_vars = set()  # Variables only used in conditional blocks

        # Helper function to extract variables from a node
        def extract_variables_from_node(node, result):
            if isinstance(node, nodes.Name):
                result.add(node.name)
            elif isinstance(node, nodes.Getattr) and isinstance(node.node, nodes.Name):
                result.add(node.node.name)
            elif isinstance(node, nodes.Filter):
                if isinstance(node.node, nodes.Name):
                    result.add(node.node.name)
                elif hasattr(node, "node"):
                    extract_variables_from_node(node.node, result)

        # Helper function to extract variables from If test conditions
        def extract_test_variables(node, result):
            if isinstance(node, nodes.Name):
                result.add(node.name)
            elif isinstance(node, nodes.BinExpr):
                extract_test_variables(node.left, result)
                extract_test_variables(node.right, result)
            elif isinstance(node, nodes.Compare):
                extract_test_variables(node.expr, result)
                for op in node.ops:
                    # Handle different Jinja2 versions - in some versions, op is a tuple,
                    # in others, it's an Operand object with an 'expr' attribute
                    if hasattr(op, "expr"):
                        extract_test_variables(op.expr, result)
                    else:
                        extract_test_variables(op[1], result)
            elif isinstance(node, nodes.Test):
                if hasattr(node, "node"):
                    extract_test_variables(node.node, result)
            elif isinstance(node, nodes.Const):
                # Constants don't contribute variable names
                pass

        # Helper to process the template
        def visit_node(node, in_conditional=False):
            if isinstance(node, nodes.If):
                # Extract variables from the test condition (always optional)
                test_vars = set()
                extract_test_variables(node.test, test_vars)
                conditional_vars.update(test_vars)

                # Process the if block
                for child in node.body:
                    visit_node(child, in_conditional=True)

                # Process the else block if it exists
                if node.else_:
                    for child in node.else_:
                        visit_node(child, in_conditional=True)

            elif isinstance(node, nodes.Output):
                # Process output expressions
                for expr in node.nodes:
                    if isinstance(expr, nodes.TemplateData):
                        # Skip plain text
                        continue

                    # Extract variables
                    vars_in_expr = set()
                    extract_variables_from_node(expr, vars_in_expr)

                    if in_conditional:
                        # Variables in conditional blocks
                        conditional_vars.update(vars_in_expr)
                    else:
                        # Variables at root level
                        root_vars.update(vars_in_expr)

            # Process other nodes recursively
            if hasattr(node, "body") and not isinstance(node, nodes.If):  # Already processed If bodies
                for child in node.body:
                    visit_node(child, in_conditional)

        # Start traversal of the template
        for node in self._ast.body:
            visit_node(node)

        # All variables in the template
        all_vars = meta.find_undeclared_variables(self._ast)

        # Required are variables at root level
        required_vars = root_vars

        # Optional are variables that ONLY appear in conditional blocks
        optional_vars = all_vars - required_vars

        return all_vars, required_vars, optional_vars

    def get_optional_variables(self) -> List[str]:
        """Return optional variables (used only in conditionals)."""
        return list(self.optional_vars)

    def get_required_variables(self) -> List[str]:
        """Return required variables (used outside conditionals)."""
        return list(self.required_vars)

    def render_template(self, variables: Dict[str, Any]) -> str:
        """Render template with variables. Validates required variables exist and aren't None.

        Raises:
            ValueError: If a required variable is missing or None
        """
        # Validate required variables
        for var in self.required_vars:
            if var == "num_records":
                continue  # num_records has default value of 1, so it is not required
            if var not in variables:
                raise ValueError(f"Required variable '{var}' is missing")
            if variables[var] is None:
                raise ValueError(f"Required variable '{var}' cannot be None")

        # Create a copy of variables to avoid modifying the original
        render_vars = variables.copy()

        # Check for list inputs with priority given to required variables
        is_list_input = False
        list_input_variable = None
        input_list_length = None

        # Check variables in priority order (required first, then optional)
        for var in list(self.required_vars) + list(self.optional_vars):
            if var in render_vars and isinstance(render_vars[var], list):
                is_list_input = True
                list_input_variable = var
                input_list_length = len(render_vars[var])
                # Add reference to the variable in the prompt before serializing
                original_list = render_vars[var]
                render_vars[var] = f"|{var}| : {json.dumps(original_list)}"
                break  # Stop after finding the first list

        # Add default None for optional variables (except for num_records which gets special treatment)
        for var in self.optional_vars:
            if var != "num_records" and var not in render_vars:
                render_vars[var] = None

        # Add list processing variables
        render_vars["is_list_input"] = is_list_input
        render_vars["list_input_variable"] = list_input_variable
        render_vars["input_list_length"] = input_list_length

        # Add default num_records (always use default value of 1 if not specified)
        render_vars["num_records"] = render_vars.get("num_records", 1)

        return self._template.render(**render_vars)

    def construct_messages(self, variables: Dict[str, Any]) -> List[Dict[str, str]]:
        """Return template rendered as a system message."""
        rendered_template = self.render_template(variables)
        return [{"role": "user", "content": rendered_template}]

    def get_printable_messages(self, messages: List[Dict[str, str]]) -> str:
        """Format constructed messages with visual separators."""
        lines = ["\n" + "=" * 80, "📝 CONSTRUCTED MESSAGES:", "=" * 80]
        for msg in messages:
            lines.append(f"\nRole: {msg['role']}\nContent:\n{msg['content']}")
        lines.extend(["\n" + "=" * 80, "End of prompt", "=" * 80 + "\n"])
        return "\n".join(lines)

    def print_template(self, variables: Dict[str, Any]) -> None:
        """Render and print template with formatting."""
        rendered = self.render_template(variables)
        print(self.get_printable_messages(rendered))


@functools.lru_cache(maxsize=32)
def get_prompt(prompt_name: str):
    """Get a complete preset prompt template that requires no additional template content."""
    if prompt_name not in COMPLETE_PROMPTS:
        available = ", ".join(COMPLETE_PROMPTS.keys())
        raise ValueError(f"Unknown complete prompt: '{prompt_name}'. Available options: {available}")

    return COMPLETE_PROMPTS[prompt_name]


@functools.lru_cache(maxsize=32)
def get_partial_prompt(prompt_name: str, template_str: str) -> PromptManager:
    """Get a partial prompt combined with user-provided template content."""
    if prompt_name not in PARTIAL_PROMPTS:
        available = ", ".join(PARTIAL_PROMPTS.keys())
        raise ValueError(f"Unknown partial prompt: '{prompt_name}'. Available options: {available}")

    partial = PARTIAL_PROMPTS[prompt_name]
    header = partial.get("header", "")
    footer = partial.get("footer", "")
    return PromptManager(template_str, header, footer)
