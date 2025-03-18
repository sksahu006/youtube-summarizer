from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
import logging

logger = logging.getLogger(__name__)

class TranscriptNotAvailable(Exception):
    pass

def get_transcript(video_id: str) -> str:
    """
    Fetch transcript prioritizing youtube-transcript-api (fastest), then pytube.
    Supports multiple languages (e.g., English, Hindi).
    """
    # Try youtube-transcript-api first (fastest)
    try:
        logger.info(f"Attempting youtube-transcript-api for video ID {video_id}")
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        preferred_langs = ['en', 'hi']

        for lang in preferred_langs:
            try:
                transcript = transcript_list.find_transcript([lang])
                transcript_text = " ".join([t["text"] for t in transcript.fetch()])
                logger.info(f"Transcript fetched with youtube-transcript-api in {lang}: {transcript_text[:50]}...")
                return transcript_text
            except Exception as e:
                logger.debug(f"No {lang} transcript available: {str(e)}")

        transcript = transcript_list.find_transcript([])
        transcript_text = " ".join([t["text"] for t in transcript.fetch()])
        logger.info(f"Transcript fetched with youtube-transcript-api in {transcript.language_code}: {transcript_text[:50]}...")
        return transcript_text
    except Exception as e:
        logger.error(f"youtube-transcript-api failed for {video_id}: {str(e)}")

    # Fallback to pytube
    try:
        logger.info(f"Attempting pytube for video ID {video_id}")
        yt = YouTube(f"https://www.youtube.com/watch?v={video_id}")
        captions = yt.captions

        if not captions:
            logger.warning(f"No captions available for {video_id} with pytube")
        else:
            preferred_langs = ['en', 'hi']
            available_captions = captions.all()
            logger.info(f"Available caption languages: {[cap.code for cap in available_captions]}")

            for lang in preferred_langs:
                caption = captions.get_by_language_code(lang)
                if caption:
                    transcript = caption.generate_srt_captions()
                    lines = [line.strip() for line in transcript.splitlines() if line.strip() and not line.strip().isdigit() and "-->" not in line]
                    transcript_text = " ".join(lines)
                    logger.info(f"Transcript fetched with pytube in {lang}: {transcript_text[:50]}...")
                    return transcript_text

            if available_captions:
                caption = available_captions[0]
                transcript = caption.generate_srt_captions()
                lines = [line.strip() for line in transcript.splitlines() if line.strip() and not line.strip().isdigit() and "-->" not in line]
                transcript_text = " ".join(lines)
                logger.info(f"Transcript fetched with pytube in {caption.code}: {transcript_text[:50]}...")
                return transcript_text

            logger.warning(f"No usable captions found for {video_id} with pytube")
    except Exception as e:
        logger.error(f"pytube failed for {video_id}: {str(e)}")

    raise TranscriptNotAvailable(f"Transcript not available for video {video_id} after trying all methods")
