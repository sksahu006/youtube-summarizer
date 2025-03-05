from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging
from api.dependencies import get_current_user, get_db
from services.transcript import get_transcript, TranscriptNotAvailable
from services.summarizer import summarize_transcript
from db.models.history import History
from core.redis import redis
from api.schemas.summarize import SummarizeRequest
from db.models.user import User
from urllib.parse import urlparse, parse_qs
import re
from typing import Literal

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter()

async def check_rate_limit(user_id: int):
    key = f"rate_limit:{user_id}"
    count = await redis.get(key)
    if count is None:
        await redis.set(key, 1, ex=3600)
    elif int(count) >= 50:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    else:
        await redis.incr(key)

def extract_video_id(link: str) -> str:
    parsed_url = urlparse(link)
    video_id = None
    query_params = parse_qs(parsed_url.query)
    
    # Check for v parameter in query string
    if "v" in query_params:
        video_id = query_params["v"][0]
    
    # Check for video ID in the path for youtu.be links
    elif "youtu.be" in parsed_url.netloc and parsed_url.path:
        path_parts = parsed_url.path.strip("/").split("/")
        if path_parts:
            video_id = path_parts[0]
    
    # Check for live stream format (/live/VIDEO_ID)
    elif "/live/" in parsed_url.path:
        path_parts = parsed_url.path.strip("/").split("/")
        try:
            live_index = path_parts.index("live")
            if live_index + 1 < len(path_parts):
                video_id = path_parts[live_index + 1]
        except ValueError:
            pass
    
    # Check embed format
    elif "embed" in parsed_url.path:
        path_parts = parsed_url.path.strip("/").split("/")
        try:
            embed_index = path_parts.index("embed")
            if embed_index + 1 < len(path_parts):
                video_id = path_parts[embed_index + 1]
        except ValueError:
            pass
    
    # Final fallback to look for anything that looks like a YouTube ID
    if not video_id:
        path_parts = parsed_url.path.strip("/").split("/")
        for part in path_parts:
            if re.match(r"[A-Za-z0-9_-]{11}", part):
                video_id = part
                break
    
    if not video_id:
        raise ValueError(f"Could not extract video ID from URL: {link}")
    
    return video_id

def is_live_stream(link: str) -> bool:
    """Check if the URL appears to be a live stream."""
    return "/live/" in link or "live=" in link

@router.post("/summarize")
async def summarize_video(
    request: SummarizeRequest,
    model: Literal["gemini", "mistral"] = "gemini",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    await check_rate_limit(current_user.id)
    try:
        link = str(request.link)
        video_id = extract_video_id(link)
        transcript = get_transcript(video_id)
        summary = await summarize_transcript(transcript, model=model)
        history = History(user_id=current_user.id, youtube_link=link, summary=summary)
        db.add(history)
        db.commit()
        return {"summary": summary}
    except TranscriptNotAvailable as e:
        logger.error(f"Transcript error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing video: {str(e)}", exc_info=True)  # Log stack trace
        raise HTTPException(status_code=400, detail=f"Error processing video: {repr(e)}")  # Use repr for full error
    finally:
        db.close()

@router.get("/history")
def get_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        history = db.query(History).filter(History.user_id == current_user.id).all()
        return [{"link": h.youtube_link, "summary": h.summary, "created_at": h.created_at} for h in history]
    finally:
        db.close()