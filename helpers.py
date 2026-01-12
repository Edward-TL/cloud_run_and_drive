"""
HELPERS FILE

PURPOSE: Helper functions for Wix Plan Sales data processing

Author: Edward Toledo Lopez <edward_tl@hotmail.com>
"""

from typing import Any
from pathlib import Path
import json
import pandas as pd

from flask import (
    Response as FlaskResponse,
    Request as FlaskRequest
)

# Path to file_manager.json
FILE_MANAGER_PATH = Path(__file__).parent / "file_manager.json"


def load_file_manager() -> dict:
    """Load file_manager.json configuration."""
    with open(FILE_MANAGER_PATH, "r") as f:
        return json.load(f)


def save_file_manager(config: dict) -> None:
    """Save updated configuration to file_manager.json."""
    with open(FILE_MANAGER_PATH, "w") as f:
        json.dump(config, f, indent=4)


def is_valid_request(request: FlaskRequest) -> tuple[FlaskResponse, dict]:
    """
    Validate if the request is valid.
    """
    if request.method != 'POST':
        bad_response = FlaskResponse(
            '{"error": "Method not allowed. Use POST."}',
            status=405,
            mimetype='application/json'
        )

    # Parse JSON body
    try:
        data = request.get_json(silent=False)
        if data is None:
            raise ValueError("Empty request body")
        return (None, data)
        
    except Exception as e:
        bad_response = FlaskResponse(
            f'{{"error": "Invalid JSON: {str(e)}"}}',
            status=400,
            mimetype='application/json'
        )
    
    return (bad_response, data)

def flat_dictionary(data: dict, prefix: str = "") -> dict:
    """
    Recursively flattens a nested dictionary into a single-level dictionary.
    
    Keys are created using underscore-separated format.
    """
    result = {}
    
    for key, value in data.items():
        new_key = f"{prefix}_{key}" if prefix else key
        
        if isinstance(value, dict):
            nested = flat_dictionary(value, new_key)
            result.update(nested)
        elif isinstance(value, list):
            if value and isinstance(value[0], dict):
                for idx, item in enumerate(value):
                    nested = flat_dictionary(item, f"{new_key}_{idx}")
                    result.update(nested)
            else:
                result[new_key] = ", ".join(str(v) for v in value)
        else:
            result[new_key] = value
            
    return result


def is_new_data(df: pd.DataFrame, new_data: dict, compare_col: str) -> bool:
    """
    Check if the new data is different from the last entry in the DataFrame.
    
    Uses timestamp or transaction ID to determine if data already exists.
    
    Args:
        df: Existing DataFrame
        new_data: New flattened data dictionary
        timestamp_col: Column to use for comparison
        
    Returns:
        True if new data should be added, False if it already exists
    """
    if df.empty:
        return True
    
    # Get the new timestamp value
    new_timestamp = new_data.get(compare_col)
    if not new_timestamp:
        return False
    
    # Check if timestamp column exists in DataFrame
    if compare_col not in df.columns:
        return False
    
    # Get last timestamp in DataFrame
    last_timestamp = df[compare_col].iloc[-1]
    
    # Compare timestamps (assuming string format that can be compared)
    return str(new_timestamp) > str(last_timestamp)

