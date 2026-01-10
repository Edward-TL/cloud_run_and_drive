"""
Google API tools needed
"""
import os
import json
import mimetypes
from collections import OrderedDict
from io import BytesIO
from dataclasses import dataclass, field
from typing import Optional

from dotenv import dotenv_values

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

import gspread


def get_env_vars(filepath: str = None) -> dict:
    """
    Reads an .env file if a path is provided,
    otherwise returns the environment variables from the OS.
    """
    if filepath and os.path.exists(filepath):
        return dotenv_values(filepath)
    
    # Return environment variables from the OS sorted alphabetically
    env_dict = OrderedDict()
    for key in sorted(os.environ.keys()):
        env_dict[key] = os.environ[key]
    return env_dict


def get_file_size(file_path: str) -> str:
    """Get human-readable file size."""
    size = os.path.getsize(file_path)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


class GoogleDrive:
    """Google Drive API wrapper class."""
    
    def __init__(self, credentials):
        self.credentials = credentials
        self.service = build('drive', 'v3', credentials=credentials)
        self.files = self.service.files()

    def create_folder(self, folder_name: str, parent_folder_id: str = None) -> str:
        """Create a folder in Google Drive and return its ID."""
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id] if parent_folder_id else []
        }

        created_folder = self.files.create(
            body=folder_metadata,
            fields='id'
        ).execute()

        print(f'Created Folder ID: {created_folder["id"]}')
        return created_folder["id"]

    def get_folder_id(self, folder_name: str, parent_folder_id: str = None) -> Optional[str]:
        """
        Get a folder's ID by its name.
        
        Args:
            folder_name: Name of the folder to find
            parent_folder_id: Optional parent folder ID to search within
            
        Returns:
            Folder ID if found, None otherwise
        """
        # Build query: search for folders with exact name
        mime_type_query = "and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        query = f"name = '{folder_name}' {mime_type_query}"
        
        if parent_folder_id:
            query += f" and '{parent_folder_id}' in parents"
        
        try:
            results = self.files.list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                pageSize=10
            ).execute()
            
            items = results.get('files', [])
            
            if items:
                # Return the first match
                return items[0]['id']
            return None
            
        except HttpError as e:
            print(f"Error searching for folder: {e}")
            return None

    def list_folder(self, parent_folder_id: str = None, delete: bool = False) -> list:
        """List folders and files in Google Drive."""
        query = f"'{parent_folder_id}' in parents and trashed=false" if parent_folder_id else None
        
        results = self.files.list(
            q=query,
            pageSize=1000,
            fields="nextPageToken, files(id, name, mimeType)"
        ).execute()
        items = results.get('files', [])

        if not items:
            print("No folders or files found in Google Drive.")
        else:
            print("Folders and files in Google Drive:")
            for item in items:
                print(f"Name: {item['name']}, ID: {item['id']}, Type: {item['mimeType']}")
                if delete:
                    self.delete_files(item['id'])
        
        return items

    def delete_files(self, file_or_folder_id: str) -> bool:
        """Delete a file or folder in Google Drive by ID."""
        try:
            self.files.delete(fileId=file_or_folder_id).execute()
            print(f"Successfully deleted file/folder with ID: {file_or_folder_id}")
            return True
        except HttpError as e:
            print(f"Error deleting file/folder with ID: {file_or_folder_id}")
            print(f"Error details: {str(e)}")
            return False

    def download_file(self, file_id: str, file_name: str = None) -> tuple[BytesIO, Optional[str]]:
        """
        Downloads a file from Google Drive.

        Args:
            file_id: The ID of the file to download.
            file_name: Optional name to save the downloaded file as.

        Returns:
            Tuple of (BytesIO buffer, file_path or None)
        """
        try:
            request = self.files.get_media(fileId=file_id)
            buffer = BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)
            
            done = False
            while not done:
                _, done = downloader.next_chunk()
            
            buffer.seek(0)
            
            # Save to file if file_name provided
            if file_name:
                file_path = os.path.join(os.getcwd(), file_name)
                with open(file_path, "wb") as f:
                    f.write(buffer.getvalue())
                buffer.seek(0)
                return buffer, file_path
            
            return buffer, None
            
        except HttpError as e:
            print(f"Error downloading file: {e}")
            return None, None

    def upload_file(self, file_name: str, file_path: str, drive_folder_id: str) -> Optional[str]:
        """
        Upload a new file to Google Drive.
        
        Args:
            file_name: Name for the file in Drive
            file_path: Local directory path containing the file
            drive_folder_id: Google Drive folder ID to upload to
            
        Returns:
            File ID if successful, None otherwise
        """
        try:
            complete_file_name = os.path.join(file_path, file_name)
            if not os.path.exists(complete_file_name):
                raise IOError(f"File does not exist: {complete_file_name}")

            file_metadata = {
                "name": file_name,
                'parents': [drive_folder_id],
            }
            
            file_type = mimetypes.guess_type(file_name)[0] or 'application/octet-stream'

            media = MediaFileUpload(complete_file_name, mimetype=file_type)
            print(f"Uploading file: {file_name} ({get_file_size(complete_file_name)})")
            
            file = self.files.create(
                body=file_metadata,
                media_body=media,
                fields="id"
            ).execute()

            file_id = file.get('id')
            print(f'File ID: {file_id}')
            return file_id

        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    def update_file(self, file_id: str, local_file_path: str) -> bool:
        """
        Update an existing file in Google Drive.
        
        Args:
            file_id: Google Drive file ID to update
            local_file_path: Local path to the file with new content
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(local_file_path):
                raise IOError(f"File does not exist: {local_file_path}")
            
            file_type = mimetypes.guess_type(local_file_path)[0] or 'application/octet-stream'
            media = MediaFileUpload(local_file_path, mimetype=file_type)
            
            print(f"Updating file: {file_id} ({get_file_size(local_file_path)})")
            
            self.files.update(
                fileId=file_id,
                media_body=media
            ).execute()
            
            print(f"Successfully updated file: {file_id}")
            return True
            
        except HttpError as error:
            print(f"Error updating file: {error}")
            return False

    def upload_buffer(self, buffer: BytesIO, file_name: str, drive_folder_id: str, 
                      mimetype: str = 'application/octet-stream') -> Optional[str]:
        """
        Upload a file from a BytesIO buffer to Google Drive.
        
        Args:
            buffer: BytesIO buffer containing the file data
            file_name: Name for the file in Drive
            drive_folder_id: Google Drive folder ID to upload to
            mimetype: MIME type of the file
            
        Returns:
            File ID if successful, None otherwise
        """
        from googleapiclient.http import MediaIoBaseUpload
        
        try:
            buffer.seek(0)
            file_metadata = {
                "name": file_name,
                'parents': [drive_folder_id],
            }
            
            media = MediaIoBaseUpload(buffer, mimetype=mimetype, resumable=True)
            
            file = self.files.create(
                body=file_metadata,
                media_body=media,
                fields="id"
            ).execute()
            
            file_id = file.get('id')
            print(f'Uploaded buffer as file ID: {file_id}')
            return file_id
            
        except HttpError as error:
            print(f"Error uploading buffer: {error}")
            return None

    def update_file_from_buffer(self, file_id: str, buffer: BytesIO, 
                                 mimetype: str = 'application/octet-stream') -> bool:
        """
        Update an existing file in Google Drive from a BytesIO buffer.
        
        Args:
            file_id: Google Drive file ID to update
            buffer: BytesIO buffer containing the new file content
            mimetype: MIME type of the file
            
        Returns:
            True if successful, False otherwise
        """
        from googleapiclient.http import MediaIoBaseUpload
        
        try:
            buffer.seek(0)
            media = MediaIoBaseUpload(buffer, mimetype=mimetype, resumable=True)
            
            self.files.update(
                fileId=file_id,
                media_body=media
            ).execute()
            
            print(f"Successfully updated file from buffer: {file_id}")
            return True
            
        except HttpError as error:
            print(f"Error updating file from buffer: {error}")
            return False


@dataclass
class GoogleEnv:
    """Google environment variables and credentials manager."""
    
    env_path: Optional[str] = None
    env_var_name: str = 'GOOGLE'
    scopes: tuple = field(default_factory=lambda: (
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/spreadsheets',
    ))
    
    # These will be set in __post_init__
    credentials: service_account.Credentials = field(init=False, default=None)
    creds_with_scope: service_account.Credentials = field(init=False, default=None)

    def __post_init__(self):
        # Load credentials info
        if self.env_path:
            # Load from .env file - expects JSON string in file
            env_vals = get_env_vars(self.env_path)
            creds_info = env_vals.get(self.env_var_name)
            if creds_info:
                creds_info = json.loads(creds_info)
            else:
                raise ValueError(f"'{self.env_var_name}' not found in {self.env_path}")
        else:
            # Load from OS environment variable
            creds_json = os.getenv(self.env_var_name)
            if not creds_json:
                raise ValueError(f"Environment variable '{self.env_var_name}' not set")
            creds_info = json.loads(creds_json)
        
        # Create credentials from service account info
        self.credentials = service_account.Credentials.from_service_account_info(creds_info)
        self.creds_with_scope = self.credentials.with_scopes(self.scopes)
    
    def sheets_client(self) -> gspread.Client:
        """Get authorized gspread client for Google Sheets."""
        return gspread.authorize(self.creds_with_scope)

    def drive_service(self) -> GoogleDrive:
        """Get GoogleDrive service instance."""
        return GoogleDrive(self.creds_with_scope)


# Create default instance (will fail if GOOGLE env var not set - catch at import time if needed)
# Google = GoogleEnv()