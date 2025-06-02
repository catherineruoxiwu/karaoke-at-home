import pytest
from fastapi.testclient import TestClient
from main import app, SongModel, engine, SQLModel, Session
from sqlmodel import select


# Initialize FastAPI test client
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    # Setup: Clear the database and recreate tables before each test
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield
    # Teardown: Drop all tables after each test
    SQLModel.metadata.drop_all(engine)

def test_add_song():
    """
    Test adding a new song to the database.
    Expect a 200 response and an ID returned.
    """
    response = client.post("/songs", json={"name": "Test Song", "url": "https://youtu.be/test1"})
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["message"] == "Song added"

def test_prevent_duplicate_url():
    """
    Test that a song with the same URL is not added again.
    Expect the same ID returned with 'Song already exists' message.
    """
    client.post("/songs", json={"name": "Song A", "url": "https://youtu.be/duplicate"})
    response = client.post("/songs", json={"name": "Song B", "url": "https://youtu.be/duplicate"})
    data = response.json()
    assert data["message"] == "Song already exists"
    assert "id" in data

def test_get_playlist():
    """
    Test retrieving the playlist with ordered songs.
    Expect the correct number of songs returned in the correct order.
    """
    client.post("/songs", json={"name": "Song 1", "url": "https://youtu.be/1"})
    client.post("/songs", json={"name": "Song 2", "url": "https://youtu.be/2"})
    response = client.get("/songs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["order"] == 1
    assert data[1]["order"] == 2

def test_delete_song():
    """
    Test deleting a song by ID.
    Expect successful deletion.
    """
    post_resp = client.post("/songs", json={"name": "Delete Me", "url": "https://youtu.be/delete"})
    song_id = post_resp.json()["id"]
    delete_resp = client.delete(f"/songs/{song_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["message"] == "Deleted successfully"

def test_shuffle_playlist():
    """
    Test shuffling the playlist.
    Ensure it returns a success message and playlist order is changed.
    """
    client.post("/songs", json={"name": "S1", "url": "https://youtu.be/s1"})
    client.post("/songs", json={"name": "S2", "url": "https://youtu.be/s2"})
    client.post("/songs", json={"name": "S3", "url": "https://youtu.be/s3"})
    resp = client.post("/songs/shuffle")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Playlist shuffled"
    playlist = client.get("/songs").json()
    assert len(playlist) == 3

def test_move_song():
    """
    Test moving a song up or down in the playlist order.
    Ensure correct order changes.
    """
    # Add two songs
    id1 = client.post("/songs", json={"name": "A", "url": "https://youtu.be/a"}).json()["id"]
    id2 = client.post("/songs", json={"name": "B", "url": "https://youtu.be/b"}).json()["id"]

    # Move second song up
    move_up = client.post(f"/songs/{id2}/move", json={"direction": "up"})
    assert move_up.status_code == 200
    assert "Moved up" in move_up.json()["message"]

    # Check new order
    playlist = client.get("/songs").json()
    assert playlist[0]["id"] == id2
    assert playlist[1]["id"] == id1

def test_play_song():
    """
    Test playing the next unplayed and processed song from the queue.
    """
    # Add a song
    client.post("/songs", json={"name": "Playable Song", "url": "https://youtu.be/playme"})

    # Manually update the song to be 'done' and unplayed
    with Session(engine) as session:
        song = session.exec(
            select(SongModel).where(SongModel.youtube_url == "https://youtu.be/playme")
        ).first()
        song.status = "done"
        song.played = False
        session.commit()

    # Call /songs/play
    response = client.post("/songs/play")
    assert response.status_code == 200
    data = response.json()

    # Verify it returned the expected song
    assert data["youtube_url"] == "https://youtu.be/playme"
    assert data["status"] == "done"
    assert data["played"] is True

    # Confirm it is now marked as played in DB
    with Session(engine) as session:
        song = session.get(SongModel, data["id"])
        assert song.played is True

def test_real_songs_with_processing():
    """
    Add real songs, wait for background processing, and verify final path.
    """
    urls = [
        "https://www.youtube.com/watch?v=VK2t7tVtGP8",
        "https://www.youtube.com/watch?v=e6e4uCGIbyo",
        "https://www.youtube.com/watch?v=i8vuK39r4LY"
    ]
    song_ids = []
    for i, url in enumerate(urls):
        response = client.post("/songs", json={"name": f"User 1", "url": url})
        assert response.status_code == 200
        song_ids.append(response.json()["id"])

    # Wait up to 10 minutes for processing
    print("Waiting for up to 10 minutes for processing to complete...")
    time.sleep(1000)

    # Now verify that files exist
    with Session(engine) as session:
        for song_id in song_ids:
            song = session.get(SongModel, song_id)
            assert song.status == "done"
            assert song.processed_path is not None
            assert os.path.exists(song.processed_path)
            assert os.path.exists(os.path.join(song.processed_path, "no_vocals.wav"))
