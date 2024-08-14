import os
from .errors import GoogleDriveError
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# File ID of Clients folder
MASTER_FILE_ID = os.environ.get("MASTER_FILE_ID")

class GoogleDriveManager:
    def __init__(self):
        self.creds = service_account.Credentials.from_service_account_file(
            'credentials.json', scopes=['https://www.googleapis.com/auth/drive']
        )

        self.service = build("drive", "v3", credentials=self.creds)

    # Create image file
    def create_image_file(self, parent_folder_id='', file_name='', file_path=''):
        try:
            file_metadata = {
                "name": f"{file_name}.webp",
                "parents": [parent_folder_id],
            }

            media = MediaFileUpload(file_path, mimetype="image/webp")
            file = self.service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        
        except HttpError:
            raise GoogleDriveError("Error uploading image file to Google Drive")

    # Create docx file
    def create_docx_file(self, parent_folder_id='', file_name='', file_path=''):
        try:
            file_metadata = {
                "name": f"{file_name}.docx",
                "parents": [parent_folder_id],
            }

            media = MediaFileUpload(file_path, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        
        except HttpError:
            raise GoogleDriveError("Error uploading docx file to Google Drive")

    # Create folder
    def create_folder(self, folder_name='', parent_folder_id=MASTER_FILE_ID):
        try:            
            file_metadata = {
                "name": folder_name,
                "parents": [parent_folder_id],
                "mimeType": "application/vnd.google-apps.folder",
            }

            file = self.service.files().create(body=file_metadata, fields="id").execute()
            return file["id"]

        except HttpError:
            return None

    # Share client's folder
    def share_folder(self, folder_id='', user_email=''):
        try:
            permissions = {
                'type': 'user',
                'role': 'writer',
                'emailAddress': user_email
            }

            response = self.service.permissions().create(fileId=folder_id, body=permissions, fields='id').execute()
        except HttpError as error:
            raise GoogleDriveError("Error sharing client's folder")

    # Checks if folder exists   
    def folder_exists(self, folder_id=''):
        try:
            file = self.service.files().get(fileId=folder_id).execute()
        except HttpError as error:
            if error.resp.status == 404:
                return False 
        return True
    
    # Delete folder from google drive
    def delete_folder(self, folder_id=''):
        try:
            file = self.service.files().delete(fileId=folder_id).execute()

        except HttpError as error:
            print("Error deleting folder", flush=True)
            raise GoogleDriveError("Error deleting folder")
