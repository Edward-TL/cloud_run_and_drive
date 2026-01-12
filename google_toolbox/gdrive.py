"""
Google API tools needed
"""
import os
from typing import Optional

import mimetypes

from io import BytesIO
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError



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
        self.file_services = self.service.files()
        self.excel_mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        self.parquet_mimetype = 'application/x-parquet'
        # self.parquet_mimetype = 'application/octet-stream'

    def create_folder(self, folder_name: str, parent_folder_id: str = None) -> str:
        """Create a folder in Google Drive and return its ID."""
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id] if parent_folder_id else []
        }

        created_folder = self.file_services.create(
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
            results = self.file_services.list(
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
            print(f"Error searching for folder:\n\n{e}")
            return None

    def get_file_id(self, file_name: str, parent_folder_id: str = None) -> Optional[str]:
        """
        Get a file's ID by its name.
        
        Args:
            file_name: Name of the file to find
            parent_folder_id: Optional parent folder ID to search within
            
        Returns:
            File ID if found, None otherwise
        """
        query = f"name = '{file_name}' and mimeType != 'application/vnd.google-apps.folder' and trashed = false"
        
        if parent_folder_id:
            query += f" and '{parent_folder_id}' in parents"
        
        try:
            results = self.file_services.list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                pageSize=10
            ).execute()
            
            items = results.get('files', [])
            
            if items:
                return items[0]['id']
            return None
            
        except HttpError as e:
            print(f"Error searching for file:\n\n{e}")
            return None

    def list_folder(self, parent_folder_id: str = None, delete: bool = False) -> list:
        """List folders and files in Google Drive."""
        query = f"'{parent_folder_id}' in parents and trashed=false" if parent_folder_id else None
        
        results = self.file_services.list(
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
            self.file_services.delete(fileId=file_or_folder_id).execute()
            print(f"Successfully deleted file/folder with ID: {file_or_folder_id}")
            return True
        except HttpError as e:
            print(f"Error deleting file/folder with ID: {file_or_folder_id}")
            print(f"Error details:\n\n{str(e)}")
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
            request = self.file_services.get_media(fileId=file_id)
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
            print(f"Error downloading file:\n\n{e}")
            return None, None

    def upload_file(self, file_name: str, file_path: str, drive_folder_id: str) -> Optional[str]:
        """
        Upload a file to Google Drive. If a file with the same name exists
        in the folder, it will be updated instead of creating a duplicate.
        
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
            
            # Check if file already exists in the folder
            existing_file_id = self.get_file_id(file_name, drive_folder_id)
            
            if existing_file_id:
                # Update existing file
                print(f"File '{file_name}' already exists. Updating...")
                success = self.update_file(existing_file_id, complete_file_name)
                return existing_file_id if success else None

            file_metadata = {
                "name": file_name,
                'parents': [drive_folder_id],
            }
            
            file_type = mimetypes.guess_type(file_name)[0] or 'application/octet-stream'

            media = MediaFileUpload(complete_file_name, mimetype=file_type)
            print(f"Uploading file: {file_name} ({get_file_size(complete_file_name)})")
            
            file = self.file_services.create(
                body=file_metadata,
                media_body=media,
                supportsAllDrives=True,
                fields="id"
            ).execute()

            file_id = file.get('id')
            print(f'File ID: {file_id}')
            return file_id

        except HttpError as error:
            print(f"An error occurred:\n\n{error}")
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
            
            self.file_services.update(
                fileId=file_id,
                media_body=media,
                supportsAllDrives=True,
                fields="id"
            ).execute()
            
            print(f"Successfully updated file: {file_id}")
            return True
            
        except HttpError as error:
            print(f"Error updating file:\n\n{error}")
            return False

    def upload_buffer(self, buffer: BytesIO, file_name: str,
                      drive_folder_id: Optional[str] = None,
                      drive_folder_name: Optional[str] = None,
                      mimetype: str = 'application/octet-stream') -> Optional[str]:
        """
        Upload a file from a BytesIO buffer to Google Drive. If a file with 
        the same name exists in the folder, it will be updated instead.
        
        Args:
            buffer: BytesIO buffer containing the file data
            file_name: Name for the file in Drive
            drive_folder_id: Google Drive folder ID to upload to
            drive_folder_name: Google Drive folder name to upload to
            mimetype: MIME type of the file
            
        Returns:
            File ID if successful, None otherwise
        """
        from googleapiclient.http import MediaIoBaseUpload
        
        if drive_folder_name:
            drive_folder_id = self.get_folder_id(drive_folder_name)
            print(drive_folder_id)
        if drive_folder_id is None:
            raise ValueError("`drive_folder_name` or `drive_folder_id` must be given")
        
        try:
            buffer.seek(0)
            
            # Check if file already exists in the folder
            existing_file_id = self.get_file_id(file_name, drive_folder_id)
            
            if existing_file_id:
                # Update existing file
                print(f"File '{file_name}' already exists. Updating...")
                success = self.update_file_from_buffer(existing_file_id, buffer, mimetype)
                return existing_file_id if success else None
            
            file_metadata = {
                "name": file_name,
                'parents': [drive_folder_id],
            }
            
            media = MediaIoBaseUpload(buffer, mimetype=mimetype, resumable=True)
            
            file = self.file_services.create(
                body=file_metadata,
                media_body=media,
                supportsAllDrives=True,
                fields="id"
            ).execute()
            
            file_id = file.get('id')
            print(f'Uploaded buffer as file ID: {file_id}')
            return file_id
            
        except HttpError as error:
            print(f"Error uploading buffer:\\n\\n{error}")
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
            
            self.file_services.update(
                fileId=file_id,
                media_body=media
            ).execute()
            
            print(f"Successfully updated file from buffer:\n\n{file_id}")
            return True
            
        except HttpError as error:
            print(f"Error updating file from buffer:\n\n{error}")
            return False

