from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Session, create_engine, select
from pydantic import BaseModel
from typing import List, Optional
import random
from concurrent.futures import ThreadPoolExecutor

from models import SongModel
from app.core.config import DATABASE_URL, cancelled_song_ids, cancelled_lock
from app.core.processor import download_and_process

executor = ThreadPoolExecutor(max_workers=1)
engine = create_engine(DATABASE_URL, echo=False)
SQLModel.metadata.create_all(engine)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # TODO: Add your frontend URL here
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SongInput(BaseModel):
    name: str
    url: str
    video: Optional[bool] = False

class MoveInput(BaseModel):
    direction: str  # "up" or "down"

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
        executor.submit(download_and_process, song, entry.id, merge_with_video=song.video)
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
