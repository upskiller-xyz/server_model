"""Unit tests for CondVecParser."""
import numpy as np
import pytest

from src.server.cond_vec import CondVecParser


class TestCondVecParser:

    def test_none_returns_none(self):
        assert CondVecParser.parse(None) is None

    def test_empty_string_returns_none(self):
        assert CondVecParser.parse("") is None

    def test_float_array_parsed_to_batched_float32(self):
        result = CondVecParser.parse("[0.5, 0.3, 0.8]")
        assert result.shape == (1, 3)
        assert result.dtype == np.float32
        np.testing.assert_allclose(result[0], [0.5, 0.3, 0.8])

    def test_integer_values_accepted(self):
        result = CondVecParser.parse("[1, 2, 3, 4]")
        assert result.shape == (1, 4)
        assert result.dtype == np.float32

    def test_invalid_json_raises_value_error(self):
        with pytest.raises(ValueError, match="not valid JSON"):
            CondVecParser.parse("not json")

    def test_non_list_raises_value_error(self):
        with pytest.raises(ValueError, match="array of numbers"):
            CondVecParser.parse('{"a": 1}')

    def test_non_numeric_element_raises_value_error(self):
        with pytest.raises(ValueError, match="array of numbers"):
            CondVecParser.parse('[1, "two", 3]')

    def test_nested_list_element_rejected(self):
        with pytest.raises(ValueError, match="array of numbers"):
            CondVecParser.parse("[[1, 2], [3, 4]]")

    def test_boolean_element_rejected(self):
        # JSON booleans are ints in Python but must not pass as numbers.
        with pytest.raises(ValueError, match="array of numbers"):
            CondVecParser.parse("[true, false]")
