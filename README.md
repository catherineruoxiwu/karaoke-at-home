# KTV @ Home

## Setup

### Frontend
```
cd frontend
pnpm install
pnpm run dev
```

### Backend
```
pip install fastapi uvicorn sqlmodel yt-dlp pydantic
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# For testing
pip install pytest
pytest test.py
```

### TODO
- [ ] Finish frontend