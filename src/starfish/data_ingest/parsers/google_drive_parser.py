from typing import Optional
from .base_parser import BaseParser


class GoogleDriveParser(BaseParser):
    def __init__(self, credentials_path: str, token_path: str):
        """Initialize Google Drive parser with credentials"""
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.scopes = ["https://www.googleapis.com/auth/drive.readonly"]
        self._service = None
        self._dependencies_loaded = False

    def _load_dependencies(self):
        """Lazy load Google Drive dependencies"""
        if not self._dependencies_loaded:
            global Credentials, InstalledAppFlow, Request, build
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build

            self._dependencies_loaded = True

    @property
    def service(self):
        """Lazy load the Google Drive service"""
        if self._service is None:
            self._load_dependencies()
            self._service = self._authenticate()
        return self._service

    def _authenticate(self):
        """Authenticate and return Google Drive service"""
        self._load_dependencies()
        creds = None
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, self.scopes)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, self.scopes)
                creds = flow.run_local_server(port=0)
            with open(self.token_path, "w") as token:
                token.write(creds.to_json())
        return build("drive", "v3", credentials=creds)

    def parse(self, file_id: str) -> str:
        """Download and parse content from Google Drive file"""
        try:
            self._load_dependencies()
            request = self.service.files().get_media(fileId=file_id)
            content = request.execute()
            return content.decode("utf-8")
        except Exception as e:
            raise Exception(f"Failed to fetch content from Google Drive: {str(e)}")
