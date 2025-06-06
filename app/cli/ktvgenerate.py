import argparse
import os
import re
import yt_dlp
from pydantic import BaseModel

from sqlmodel import SQLModel, create_engine
from app.models.song import SongModel
from app.core.config import DATABASE_URL
from app.core.processor import download_and_process

engine = create_engine(DATABASE_URL, echo=False)
SQLModel.metadata.create_all(engine)

class CLISongInput(BaseModel):
    name: str = "cli_user"
    url: str
    video: bool = False

def cli_download(link: str, download_video: bool = False):
    song_input = CLISongInput(url=link, video=download_video)
    download_and_process(song_input, song_id=-1, merge_with_video=download_video)

def main():
    parser = argparse.ArgumentParser(description="🎤 KTV Generate CLI")
    parser.add_argument("--link", required=True, help="YouTube link to download")
    parser.add_argument("--video", action="store_true", help="Download full video instead of audio")
    args = parser.parse_args()
    cli_download(args.link, args.video)

if __name__ == "__main__":
    main()