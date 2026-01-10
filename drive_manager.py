
from io import BytesIO

from google.oauth2 import service_account
from googleapiclient.discovery import build, Resource
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

def get_drive_service(credentials_path: str = None) -> Resource:
    """
    Initialize and return a Google Drive API service client.
    
    Args:
        credentials_path: Path to service account JSON file.
                         If None, uses default credentials (Cloud Run environment)
    
    Returns:
        Google Drive API service client
    """
    scopes = ['https://www.googleapis.com/auth/drive']
    
    if credentials_path:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=scopes
        )
    else:
        # Use default credentials in Cloud Run environment
        from google.auth import default
        credentials, _ = default(scopes=scopes)
    
    return build('drive', 'v3', credentials=credentials)

def download_excel(drive_service: Resource, file_id: str) -> BytesIO:
    """
    Download an Excel file from Google Drive.
    
    Args:
        drive_service: Google Drive API service client
        file_id: The Google Drive file ID
        
    Returns:
        BytesIO buffer containing the Excel file data
    """
    request = drive_service.files().get_media(fileId=file_id)
    buffer = BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    
    done = False
    while not done:
        _, done = downloader.next_chunk()
    
    buffer.seek(0)
    return buffer

def upload_excel(drive_service, file_id: str, workbook: Workbook) -> None:
    """
    Upload/update an Excel file to Google Drive.
    
    Args:
        drive_service: Google Drive API service client
        file_id: The Google Drive file ID to update
        workbook: The openpyxl Workbook to upload
    """
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    
    media = MediaIoBaseUpload(
        buffer,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        resumable=True
    )
    
    drive_service.files().update(
        fileId=file_id,
        media_body=media
    ).execute()
