from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from . import config

_service = None


def service():
    global _service
    if _service is None:
        _service = build("drive", "v3", credentials=config.google_credentials())
    return _service


def upload_public(path: str, name: str) -> str:
    """Upload a file, make it public, return a direct-view URL usable by APIs."""
    media = MediaFileUpload(path, mimetype="image/jpeg")
    body = {"name": name}
    if config.DRIVE_FOLDER_ID:
        body["parents"] = [config.DRIVE_FOLDER_ID]
    file = service().files().create(body=body, media_body=media, fields="id").execute()
    file_id = file["id"]
    service().permissions().create(
        fileId=file_id, body={"role": "reader", "type": "anyone"}
    ).execute()
    return f"https://drive.google.com/uc?export=view&id={file_id}"
