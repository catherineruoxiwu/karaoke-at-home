import os
import re
import subprocess
import yt_dlp
from sqlmodel import Session
from app.core.config import SONG_DIR, SEPARATED_DIR, PROCESSED_DIR, cancelled_song_ids, cancelled_lock, DATABASE_URL
from app.models.song import SongModel
from sqlmodel import create_engine

engine = create_engine(DATABASE_URL, echo=False)

def sanitize_filename(text):
    return re.sub(r'[^a-zA-Z0-9-_\.]+', '_', text)

def download_and_process(song, song_id: int = None, merge_with_video: bool = False, from_cli: bool = False):
    try:
        is_cli = from_cli

        with cancelled_lock:
            if not is_cli and song_id in cancelled_song_ids:
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

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(song.url, download=True)
            with cancelled_lock:
                if not is_cli and song_id in cancelled_song_ids:
                    print(f"Processing of song {song_id} cancelled after download.")
                    return

            filepath = ydl.prepare_filename(info)
            title = os.path.splitext(os.path.basename(filepath))[0]
            mp3_path = os.path.join(SONG_DIR, f"{title}.mp3")

        safe_name = sanitize_filename(f"{title}_{song.url}")
        final_song_dir = os.path.join(PROCESSED_DIR, safe_name)
        if os.path.exists(os.path.join(final_song_dir, "no_vocals.wav")):
            if not is_cli:
                with Session(engine) as session:
                    db_song = session.get(SongModel, song_id)
                    if db_song:
                        db_song.processed_path = final_song_dir
                        db_song.instrumental = os.path.join(final_song_dir, "no_vocals.wav")
                        db_song.vocals = os.path.join(final_song_dir, "vocals.wav")
                        db_song.status = "done"
                        session.commit()
            return

        if not is_cli:
            with Session(engine) as session:
                db_song = session.get(SongModel, song_id)
                if db_song:
                    db_song.title = title
                    session.commit()

        subprocess.run([
            "demucs", "--two-stems=vocals", "-n", "mdx_extra", mp3_path
        ], check=True)

        with cancelled_lock:
            if not is_cli and song_id in cancelled_song_ids:
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

        if merge_with_video:
            video_opts = {
                'format': 'bestvideo+bestaudio/best',
                'outtmpl': f'{SONG_DIR}/%(title)s.%(ext)s',
                'merge_output_format': 'mp4',
            }
            with yt_dlp.YoutubeDL(video_opts) as ydl:
                video_info = ydl.extract_info(song.url, download=True)
                original_video_path = ydl.prepare_filename(video_info)

            merged_output = os.path.join(final_song_dir, "merged_video.mp4")
            cmd = [
                "ffmpeg",
                "-i", original_video_path,
                "-i", final_no_vocals,
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "libx264", "-preset", "veryfast",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest", "-movflags", "+faststart",
                "-y", merged_output
            ]
            subprocess.run(cmd, check=True)

            if not is_cli:
                with Session(engine) as session:
                    db_song = session.get(SongModel, song_id)
                    if db_song:
                        db_song.merged_video = merged_output
                        db_song.processed_path = final_song_dir
                        db_song.status = "done"
                        session.commit()
            if is_cli:
                print(f"🎥 Merged KTV video saved to: {merged_output}")
            return

        if not is_cli:
            with Session(engine) as session:
                db_song = session.get(SongModel, song_id)
                if db_song:
                    db_song.instrumental = final_no_vocals if os.path.exists(final_no_vocals) else None
                    db_song.vocals = final_vocals if os.path.exists(final_vocals) else None
                    db_song.processed_path = final_song_dir
                    db_song.status = "done"
                    session.commit()

        if is_cli:
            print(f"🎵 Instrumental saved to: {final_no_vocals}")

    except Exception as e:
        print("Download/process error:", e)
        if not is_cli:
            with Session(engine) as session:
                db_song = session.get(SongModel, song_id)
                if db_song:
                    db_song.status = "error"
                    session.commit()
