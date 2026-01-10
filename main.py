"""
MAIN FILE

PURPOSE: Cloud Run function to receive Wix Plan Sales webhooks
         and store data in Google Drive (Parquet + Excel)

Author: Edward Toledo Lopez <edward_tl@hotmail.com>
"""

import os
import json
from io import BytesIO
from pathlib import Path

import pandas as pd
from functions_framework import http as functions_http
from flask import Response as FlaskResponse, Request as FlaskRequest

from google import GoogleEnv

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


def is_new_data(df: pd.DataFrame, new_data: dict, timestamp_col: str = "plan_start_date") -> bool:
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
    new_timestamp = new_data.get(timestamp_col)
    if not new_timestamp:
        # If no timestamp, check plan_order_id as fallback
        order_id_col = "plan_order_id"
        new_order_id = new_data.get(order_id_col)
        if new_order_id and order_id_col in df.columns:
            return new_order_id not in df[order_id_col].values
        return True
    
    # Check if timestamp column exists in DataFrame
    if timestamp_col not in df.columns:
        return True
    
    # Get last timestamp in DataFrame
    last_timestamp = df[timestamp_col].iloc[-1]
    
    # Compare timestamps (assuming string format that can be compared)
    return str(new_timestamp) > str(last_timestamp)


@functions_http
def load_to_excel(request: FlaskRequest) -> FlaskResponse:
    """
    HTTP entry point for receiving Wix Plan Sales data.
    
    Receives a POST request with JSON body from Wix API,
    flattens the data, and stores in Parquet + Excel files on Google Drive.
    
    Returns:
        FlaskResponse with status and message
    """
    # Only accept POST requests
    if request.method != 'POST':
        return FlaskResponse(
            '{"error": "Method not allowed. Use POST."}',
            status=405,
            mimetype='application/json'
        )
    
    # Parse JSON body
    try:
        data = request.get_json(silent=False)
        if data is None:
            raise ValueError("Empty request body")
    except Exception as e:
        return FlaskResponse(
            f'{{"error": "Invalid JSON: {str(e)}"}}',
            status=400,
            mimetype='application/json'
        )
    
    # Load configuration
    try:
        config = load_file_manager()
        file_name = config.get("FILE_NAME", "COMPRAS_PAQUETES_DHELOS")
        parquet_file_id = config.get("PARQUET_FILE_ID", "")
        excel_file_id = config.get("EXCEL_FILE_ID", "")
        folder_id = config.get("GOOGLE_DRIVE_FOLDER_ID", "")
    except Exception as e:
        return FlaskResponse(
            f'{{"error": "Failed to load config: {str(e)}"}}',
            status=500,
            mimetype='application/json'
        )
    
    # Validate folder ID
    if not folder_id:
        return FlaskResponse(
            '{"error": "GOOGLE_DRIVE_FOLDER_ID not configured in file_manager.json"}',
            status=500,
            mimetype='application/json'
        )
    
    # Initialize Google Drive
    try:
        google_env = GoogleEnv()
        drive = google_env.drive_service()
    except Exception as e:
        return FlaskResponse(
            f'{{"error": "Failed to initialize Google Drive: {str(e)}"}}',
            status=500,
            mimetype='application/json'
        )
    
    # Flatten the nested dictionary
    flat_data = flat_dictionary(data)
    df_new = pd.DataFrame([flat_data])
    
    # Step 1: Check if file exists
    updated_df = False
    
    if parquet_file_id:
        # Step 2.a: File exists - download and check for new data
        try:
            buffer, _ = drive.download_file(parquet_file_id)
            if buffer:
                df = pd.read_parquet(buffer)
                updated_df = is_new_data(df, flat_data)
            else:
                # Download failed, treat as new file
                df = pd.DataFrame()
                updated_df = True
        except Exception as e:
            print(f"Error reading parquet: {e}")
            df = pd.DataFrame()
            updated_df = True
    else:
        # Step 2.b: File does not exist
        df = pd.DataFrame()
        updated_df = True
    
    # Step 3: Update DataFrame if needed
    if not updated_df:
        return FlaskResponse(
            '{"status": "skipped", "message": "Data already exists in file"}',
            status=200,
            mimetype='application/json'
        )
    
    # Append new data
    df = pd.concat([df, df_new], ignore_index=True)
    
    # Step 4: Save and upload Parquet file
    try:
        parquet_buffer = BytesIO()
        df.to_parquet(parquet_buffer, index=False)
        parquet_buffer.seek(0)
        
        if parquet_file_id:
            # Update existing file
            drive.update_file_from_buffer(
                parquet_file_id, 
                parquet_buffer, 
                mimetype='application/octet-stream'
            )
        else:
            # Create new file
            parquet_file_id = drive.upload_buffer(
                parquet_buffer,
                f"{file_name}.parquet",
                folder_id,
                mimetype='application/octet-stream'
            )
            config["PARQUET_FILE_ID"] = parquet_file_id
    except Exception as e:
        return FlaskResponse(
            f'{{"error": "Failed to save parquet: {str(e)}"}}',
            status=500,
            mimetype='application/json'
        )
    
    # Step 5: Save and upload Excel file
    try:
        excel_buffer = BytesIO()
        df.to_excel(excel_buffer, index=False, sheet_name="VENTAS DHELOS")
        excel_buffer.seek(0)
        
        excel_mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        if excel_file_id:
            # Update existing file
            drive.update_file_from_buffer(
                excel_file_id, 
                excel_buffer, 
                mimetype=excel_mimetype
            )
        else:
            # Create new file
            excel_file_id = drive.upload_buffer(
                excel_buffer,
                f"{file_name}.xlsx",
                folder_id,
                mimetype=excel_mimetype
            )
            config["EXCEL_FILE_ID"] = excel_file_id
    except Exception as e:
        return FlaskResponse(
            f'{{"error": "Failed to save excel: {str(e)}"}}',
            status=500,
            mimetype='application/json'
        )
    
    # Step 6: Update file_manager.json
    try:
        save_file_manager(config)
    except Exception as e:
        print(f"Warning: Failed to update file_manager.json: {e}")
    
    return FlaskResponse(
        f'{{"status": "success", "message": "Data added", "rows": {len(df)}, "parquet_id": "{parquet_file_id}", "excel_id": "{excel_file_id}"}}',
        status=200,
        mimetype='application/json'
    )