"""
HELPERS FILE

PURPOSE: Helper functions for Wix Plan Sales data processing

Author: Edward Toledo Lopez <edward_tl@hotmail.com>
"""

from typing import Any


def flat_dictionary(data: dict, prefix: str = "") -> dict:
    """
    Recursively flattens a nested dictionary into a single-level dictionary.
    
    Keys are created using underscore-separated format:
    - root_key_nested_key for nested values
    - root_key for top-level values
    
    Args:
        data: The dictionary to flatten
        prefix: The prefix to prepend to keys (used for recursion)
        
    Returns:
        A flat dictionary with underscore-separated keys
        
    Example:
        >>> flat_dictionary({"contact": {"name": {"first": "John"}}})
        {"contact_name_first": "John"}
    """
    result = {}
    
    for key, value in data.items():
        # Build the new key with prefix if present
        new_key = f"{prefix}_{key}" if prefix else key
        
        if isinstance(value, dict):
            # Recursively flatten nested dictionaries
            nested = flat_dictionary(value, new_key)
            result.update(nested)
        elif isinstance(value, list):
            # Handle lists - join items or store as-is for simple values
            if value and isinstance(value[0], dict):
                # List of dicts: flatten each with index
                for idx, item in enumerate(value):
                    nested = flat_dictionary(item, f"{new_key}_{idx}")
                    result.update(nested)
            else:
                # Simple list: join as comma-separated string
                result[new_key] = ", ".join(str(v) for v in value)
        else:
            result[new_key] = value
            
    return result



