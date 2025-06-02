from sqlmodel import SQLModel, Field, Session, create_engine, select
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import subprocess
import yt_dlp
import os
from concurrent.futures import ThreadPoolExecutor
import random
from fastapi.middleware.cors import CORSMiddleware
from threading import Lock
import re

# Setup
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://192.168.189.205:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
executor = ThreadPoolExecutor(max_workers=1)
DATABASE_URL = "sqlite:///songs.db"
engine = create_engine(DATABASE_URL, echo=False)

# Directories
SONG_DIR = "downloads"
SEPARATED_DIR = "separated"
PROCESSED_DIR = "processed"
os.makedirs(SONG_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Cancellation
cancelled_song_ids = set()
cancelled_lock = Lock()

# DB Models
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

class SongInput(BaseModel):
    name: str
    url: str

class MoveInput(BaseModel):
    direction: str  # "up" or "down"

SQLModel.metadata.create_all(engine)

def sanitize_filename(text):
    return re.sub(r'[^a-zA-Z0-9-_\.]+', '_', text)

# Processing Function
def download_and_process(song: SongInput, song_id: int):
    try:
        with cancelled_lock:
            if song_id in cancelled_song_ids:
                print(f"Processing of song {song_id} cancelled before start.")
                return

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{SONG_DIR}/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        title = ""
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(song.url, download=True)
            with cancelled_lock:
                if song_id in cancelled_song_ids:
                    print(f"Processing of song {song_id} cancelled after download.")
                    return

            filepath = ydl.prepare_filename(info)
            title = os.path.splitext(os.path.basename(filepath))[0]
            mp3_path = os.path.join(SONG_DIR, f"{title}.mp3")

        # Update title in DB immediately after download
        safe_name = sanitize_filename(f"{title}_{song.url}")
        print("safe_name:", safe_name)
        final_song_dir = os.path.join(PROCESSED_DIR, safe_name)
        if os.path.exists(os.path.join(final_song_dir, "no_vocals.wav")):
            print(f"Skipping processing for {title} ({song_id}) - already exists.")
            with Session(engine) as session:
                db_song = session.get(SongModel, song_id)
                db_song.processed_path = final_song_dir
                db_song.instrumental = os.path.join(final_song_dir, "no_vocals.wav")
                db_song.vocals = os.path.join(final_song_dir, "vocals.wav")
                db_song.status = "done"
                session.commit()
            return

        with Session(engine) as session:
            db_song = session.get(SongModel, song_id)
            db_song.title = title
            session.commit()

        subprocess.run([
            "demucs", "--two-stems=vocals", "-n", "mdx_extra", mp3_path
        ], check=True)

        with cancelled_lock:
            if song_id in cancelled_song_ids:
                print(f"Processing of song {song_id} cancelled after demucs.")
                return

        original_no_vocals = os.path.join(SEPARATED_DIR, "mdx_extra", title, "no_vocals.wav")
        original_vocals = os.path.join(SEPARATED_DIR, "mdx_extra", title, "vocals.wav")
        os.makedirs(final_song_dir, exist_ok=True)
        final_no_vocals = os.path.join(final_song_dir, "no_vocals.wav")
        final_vocals = os.path.join(final_song_dir, "vocals.wav")

        if os.path.exists(original_no_vocals):
            os.rename(original_no_vocals, final_no_vocals)
        if os.path.exists(original_vocals):
            os.rename(original_vocals, final_vocals)
        if os.path.exists(mp3_path):
            os.remove(mp3_path)

        with Session(engine) as session:
            db_song = session.get(SongModel, song_id)
            db_song.instrumental = final_no_vocals if os.path.exists(final_no_vocals) else None
            db_song.vocals = final_vocals if os.path.exists(final_vocals) else None
            db_song.processed_path = final_song_dir
            db_song.status = "done"
            session.commit()

    except Exception as e:
        print("Download/process error:", e)
        with Session(engine) as session:
            db_song = session.get(SongModel, song_id)
            db_song.status = "error"
            session.commit()

# APIs
@app.post("/songs")
def add_song(song: SongInput):
    with Session(engine) as session:
        existing = session.exec(select(SongModel).where(SongModel.youtube_url == song.url)).first()
        if existing:
            return {"message": "Song already exists", "id": existing.id}

        max_order = session.exec(select(SongModel.order).order_by(SongModel.order.desc())).first()
        new_order = (max_order or 0) + 1
        entry = SongModel(
            title="processing",
            singer=song.name,
            youtube_url=song.url,
            status="processing",
            order=new_order
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)
        executor.submit(download_and_process, song, entry.id)
        return {"message": "Song added", "id": entry.id}

@app.post("/songs/play", response_model=SongModel)
def play_song():
    with Session(engine) as session:
        song = session.exec(
            select(SongModel)
            .where((SongModel.status == "done") & (SongModel.played == False))
            .order_by(SongModel.order)
        ).first()

        if not song:
            raise HTTPException(status_code=404, detail="No song available")

        song.played = True
        session.commit()
        return SongModel.from_orm(song)

@app.delete("/songs/{id}")
def delete_song(id: int):
    with Session(engine) as session:
        song = session.get(SongModel, id)
        if not song:
            raise HTTPException(status_code=404, detail="Song not found")

        with cancelled_lock:
            cancelled_song_ids.add(id)

        session.delete(song)
        session.commit()
        return {"message": "Deleted successfully"}

@app.post("/songs/{id}/move")
def move_song(id: int, move: MoveInput):
    with Session(engine) as session:
        song = session.get(SongModel, id)
        if not song:
            raise HTTPException(status_code=404, detail="Song not found")

        songs = session.exec(select(SongModel).order_by(SongModel.order)).all()
        index = next((i for i, s in enumerate(songs) if s.id == id), None)

        if move.direction == "up" and index > 0:
            above = songs[index - 1]
            song.order, above.order = above.order, song.order
        elif move.direction == "down" and index < len(songs) - 1:
            below = songs[index + 1]
            song.order, below.order = below.order, song.order
        else:
            raise HTTPException(status_code=400, detail="Cannot move in that direction")

        session.commit()
        return {"message": f"Moved {move.direction}"}

@app.post("/songs/shuffle")
def shuffle_playlist():
    with Session(engine) as session:
        songs = session.exec(select(SongModel).order_by(SongModel.order)).all()
        random.shuffle(songs)
        for i, song in enumerate(songs):
            song.order = i + 1
        session.commit()
        return {"message": "Playlist shuffled"}

@app.get("/songs", response_model=List[SongModel])
def get_playlist():
    with Session(engine) as session:
        return session.exec(
            select(SongModel)
            .where(SongModel.played == False)
            .order_by(SongModel.order)
        ).all()