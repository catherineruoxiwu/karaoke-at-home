from sqlmodel import SQLModel, Field
from typing import Optional

class SongModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    singer: str
    youtube_url: str
    instrumental: Optional[str] = None
    vocals: Optional[str] = None
    processed_path: Optional[str] = None
    status: str
    order: int
    played: Optional[bool] = False
    merged_video: Optional[str] = None
