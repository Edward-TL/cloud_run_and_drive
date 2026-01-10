"""
Unit tests for helpers.py

Run with: python -m pytest tests/test_helpers.py -v
"""

import pytest
from helpers import flat_dictionary


class TestFlatDictionary:
    """Tests for the flat_dictionary function."""
    
    def test_simple_flat_dict(self):
        """Test with already flat dictionary."""
        data = {"name": "John", "age": 30}
        result = flat_dictionary(data)
        
        assert result == {"name": "John", "age": 30}
    
    def test_nested_dict(self):
        """Test with one level of nesting."""
        data = {
            "contact": {
                "name": "John",
                "email": "john@example.com"
            }
        }
        result = flat_dictionary(data)
        
        assert result == {
            "contact_name": "John",
            "contact_email": "john@example.com"
        }
    
    def test_deeply_nested_dict(self):
        """Test with multiple levels of nesting."""
        data = {
            "contact": {
                "name": {
                    "first": "John",
                    "last": "Doe"
                }
            }
        }
        result = flat_dictionary(data)
        
        assert result == {
            "contact_name_first": "John",
            "contact_name_last": "Doe"
        }
    
    def test_mixed_types(self):
        """Test with various value types."""
        data = {
            "string": "hello",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None
        }
        result = flat_dictionary(data)
        
        assert result["string"] == "hello"
        assert result["number"] == 42
        assert result["float"] == 3.14
        assert result["boolean"] is True
        assert result["null"] is None
    
    def test_simple_list(self):
        """Test with list of simple values."""
        data = {
            "tags": ["python", "flask", "cloud"]
        }
        result = flat_dictionary(data)
        
        assert result["tags"] == "python, flask, cloud"
    
    def test_list_of_dicts(self):
        """Test with list of dictionaries."""
        data = {
            "items": [
                {"id": 1, "name": "Item 1"},
                {"id": 2, "name": "Item 2"}
            ]
        }
        result = flat_dictionary(data)
        
        assert result["items_0_id"] == 1
        assert result["items_0_name"] == "Item 1"
        assert result["items_1_id"] == 2
        assert result["items_1_name"] == "Item 2"
    
    def test_wix_payload_structure(self):
        """Test with structure similar to Wix API payload."""
        data = {
            "plan_title": "Yoga Course",
            "plan_price": {
                "value": "20",
                "currency": "USD"
            },
            "contact": {
                "name": {
                    "first": "Jamie",
                    "last": "Brooks"
                },
                "email": "example@email.com"
            }
        }
        result = flat_dictionary(data)
        
        assert result["plan_title"] == "Yoga Course"
        assert result["plan_price_value"] == "20"
        assert result["plan_price_currency"] == "USD"
        assert result["contact_name_first"] == "Jamie"
        assert result["contact_name_last"] == "Brooks"
        assert result["contact_email"] == "example@email.com"
    
    def test_empty_dict(self):
        """Test with empty dictionary."""
        result = flat_dictionary({})
        assert result == {}
    
    def test_with_prefix(self):
        """Test using a custom prefix."""
        data = {"key": "value"}
        result = flat_dictionary(data, prefix="root")
        
        assert result == {"root_key": "value"}
