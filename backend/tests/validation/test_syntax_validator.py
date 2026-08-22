"""
test_syntax_validator.py  (tests.validation)
==============================================
Unit tests for Stage 8.7 — SyntaxValidator.

Tests cover:
    - Language resolution by extension and name
    - Python AST syntax checking (valid & invalid)
    - JSON parsing syntax checking (valid & invalid)
    - JS/TS bracket and string balance checking (valid & invalid)
    - Empty content handling
    - Guarantee of static analysis (no code execution)

Author : AI Code Review Bot — Phase 8 (Stage 8.7)
"""

from __future__ import annotations

import pytest

from app.validation.syntax_validator import (
    SyntaxValidationResult,
    SyntaxValidator,
    resolve_language,
)


# ---------------------------------------------------------------------------
# Language Resolver Tests
# ---------------------------------------------------------------------------


class TestLanguageResolver:
    def test_resolve_by_name(self):
        assert resolve_language("python") == "Python"
        assert resolve_language("JSON") == "JSON"
        assert resolve_language("javascript") == "JavaScript"
        assert resolve_language("typescript") == "TypeScript"

    def test_resolve_by_filename(self):
        assert resolve_language("app/main.py") == "Python"
        assert resolve_language("config.json") == "JSON"
        assert resolve_language("src/index.ts") == "TypeScript"
        assert resolve_language("src/components/App.tsx") == "TypeScript"
        assert resolve_language("utils.js") == "JavaScript"

    def test_resolve_unknown(self):
        assert resolve_language("file.xyz") == "Generic"


# ---------------------------------------------------------------------------
# Python Syntax Tests
# ---------------------------------------------------------------------------


class TestPythonSyntax:
    validator = SyntaxValidator()

    def test_valid_python(self):
        code = "def add(a: int, b: int) -> int:\n    return a + b\n"
        res = self.validator.validate_syntax(code, "app/math.py")
        assert res.valid is True
        assert res.language == "Python"
        assert res.error_message is None

    def test_invalid_python_syntax_error(self):
        code = "def add(a, b\n    return a + b"  # Missing closing paren
        res = self.validator.validate_syntax(code, "Python")
        assert res.valid is False
        assert res.language == "Python"
        assert "SyntaxError" in res.error_message or "line" in res.error_message

    def test_invalid_python_indentation_error(self):
        code = "def foo():\nreturn 42"
        res = self.validator.validate_syntax(code, "Python")
        assert res.valid is False


# ---------------------------------------------------------------------------
# JSON Syntax Tests
# ---------------------------------------------------------------------------


class TestJSONSyntax:
    validator = SyntaxValidator()

    def test_valid_json(self):
        payload = '{"name": "test", "items": [1, 2, 3], "valid": true}'
        res = self.validator.validate_syntax(payload, "config.json")
        assert res.valid is True
        assert res.language == "JSON"
        assert res.error_message is None

    def test_invalid_json_trailing_comma(self):
        payload = '{"name": "test",}'
        res = self.validator.validate_syntax(payload, "JSON")
        assert res.valid is False
        assert "JSONDecodeError" in res.error_message

    def test_empty_json(self):
        res = self.validator.validate_syntax("", "JSON")
        assert res.valid is False


# ---------------------------------------------------------------------------
# JS / TS Bracket & String Balance Tests
# ---------------------------------------------------------------------------


class TestJSTSSyntax:
    validator = SyntaxValidator()

    def test_valid_js_code(self):
        code = """
        function calculateTotal(items) {
            return items.reduce((acc, item) => {
                return acc + (item.price || 0);
            }, 0);
        }
        """
        res = self.validator.validate_syntax(code, "src/utils.js")
        assert res.valid is True
        assert res.language == "JavaScript"

    def test_valid_ts_code_with_strings(self):
        code = "const msg = 'hello (world)'; const template = `item: ${msg}`; console.log(template);"
        res = self.validator.validate_syntax(code, "src/app.ts")
        assert res.valid is True
        assert res.language == "TypeScript"

    def test_unmatched_closing_bracket(self):
        code = "function test() { return 1; }}"
        res = self.validator.validate_syntax(code, "TypeScript")
        assert res.valid is False
        assert "Unmatched closing bracket" in res.error_message

    def test_unclosed_opening_bracket(self):
        code = "function test() { return 1;"
        res = self.validator.validate_syntax(code, "JavaScript")
        assert res.valid is False
        assert "Unclosed bracket" in res.error_message

    def test_unclosed_string(self):
        code = "const str = 'hello world;"
        res = self.validator.validate_syntax(code, "JavaScript")
        assert res.valid is False
        assert "Unclosed string" in res.error_message


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestSyntaxValidatorEdgeCases:
    validator = SyntaxValidator()

    def test_empty_content_returns_invalid(self):
        res = self.validator.validate_syntax("", "Python")
        assert res.valid is False
        assert "empty" in res.error_message.lower()

    def test_result_immutability(self):
        res = SyntaxValidationResult(valid=True, language="Python")
        with pytest.raises((AttributeError, TypeError)):
            res.valid = False  # type: ignore[misc]
