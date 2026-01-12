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
from flask import (
    Response as FlaskResponse,
    Request as FlaskRequest
)

from google_toolbox.gdrive import GoogleEnv

from helpers import (
    is_valid_request,
    load_file_manager,
    save_file_manager,
    flat_dictionary,
    is_new_data
)

@functions_http
def load_sales_files(request: FlaskRequest) -> FlaskResponse:
    """
    HTTP entry point for receiving Wix Plan Sales data.
    
    Receives a POST request with JSON body from Wix API,
    flattens the data, and stores in Parquet + Excel files on Google Drive.
    
    Returns:
        FlaskResponse with status and message
    """
    # Only accept POST requests
    bad_response, data = is_valid_request(request)
    if bad_response is not None:
        return bad_response

    # Load configuration
    try:
        file_name = os.getenv("FILE_NAME")
        folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        timestamp_column = os.getenv("TIMESTAMP_COLUMN")
        
        config = load_file_manager()
        parquet_file_id = config.get("PARQUET_FILE_ID")
        excel_file_id = config.get("EXCEL_FILE_ID")

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
        google_env = GoogleEnv(
            
        )
        drive = google_env.drive_service()
    except Exception as e:
        return FlaskResponse(
            f'{{"error": "Failed to initialize Google Drive: {str(e)}"}}',
            status=500,
            mimetype='application/json'
        )
    
    # Confirm the existence of the parquet_id:
    if parquet_file_id is None:
        parquet_file_id = drive.get_file_id(f"{file_name}.parquet")
        excel_file_id = drive.get_file_id(f"{file_name}.xlsx")
            

    # Flatten the nested dictionary
    flat_data = flat_dictionary(data)
    
    # Step 1: Check if file exists
    update_df = False
    if parquet_file_id:
        # Step 2.a: File exists - download and check for new data
        try:
            buffer, _ = drive.download_file(parquet_file_id)
            if buffer:
                df = pd.read_parquet(buffer)
                update_df = is_new_data(df, flat_data)
            else:
                # Download failed, treat as new file
                df = pd.DataFrame()
                update_df = True
        except Exception as e:
            return FlaskResponse(
                f'{{"error": "Failed to download parquet: {str(e)}"}}',
                status=500,
                mimetype='application/json'
            )
    else:
        # Step 2.b: File does not exist
        df = pd.DataFrame()
        update_df = True
    
    
    df_new = pd.DataFrame([flat_data])
    
    # Step 3.a: If update is not needed
    if not update_df:
        return FlaskResponse(
            '{"status": "skipped", "message": "Data already exists in file"}',
            status=200,
            mimetype='application/json'
        )
    
    # Step 3.b: Update DataFrame if needed
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
                mimetype=drive.parquet_mimetype
            )
        else:
            # Create new file
            parquet_file_id = drive.upload_buffer(
                parquet_buffer,
                f"{file_name}.parquet",
                folder_id,
                mimetype = drive.parquet_mimetype
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
        
        if excel_file_id:
            # Update existing file
            drive.update_file_from_buffer(
                excel_file_id, 
                excel_buffer, 
                mimetype=drive.excel_mimetype
            )
        else:
            # Create new file
            excel_file_id = drive.upload_buffer(
                excel_buffer,
                f"{file_name}.xlsx",
                folder_id,
                mimetype = drive.excel_mimetype
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