from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import logging
import time

logger = logging.getLogger(__name__)

class TranscriptNotAvailable(Exception):
    pass

def get_transcript(video_id: str) -> str:
    """
    Fetch transcript prioritizing youtube-transcript-api (fastest), then pytube, then selenium.
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

    # Fallback to selenium
    driver = None  # Initialize driver outside the try block
    try:
        logger.info(f"Attempting selenium for video ID {video_id}")
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in background
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(f"https://www.youtube.com/watch?v={video_id}")
        time.sleep(3)  # Wait for page to load

        # Enable captions if available
        try:
            settings_button = driver.find_element(By.XPATH, "//button[@aria-label='Settings']")
            settings_button.click()
            time.sleep(1)
            captions_option = driver.find_element(By.XPATH, "//div[contains(text(), 'Subtitles/CC')]")
            captions_option.click()
            time.sleep(1)
            driver.find_element(By.XPATH, "//div[contains(text(), 'Auto-translate') or contains(text(), 'English') or contains(text(), 'Hindi')]").click()
        except Exception as e:
            logger.debug(f"Could not enable captions manually: {str(e)}")

        # Extract transcript from captions container
        transcript_elements = driver.find_elements(By.CLASS_NAME, "ytp-caption-segment")
        if transcript_elements:
            transcript_text = " ".join([element.text for element in transcript_elements if element.text])
            logger.info(f"Transcript fetched with selenium: {transcript_text[:50]}...")
            return transcript_text
        else:
            logger.warning(f"No captions found with selenium for {video_id}")
    except Exception as e:
        logger.error(f"selenium failed for {video_id}: {str(e)}")
    finally:
        if driver:
            driver.quit()

    raise TranscriptNotAvailable(f"Transcript not available for video {video_id} after trying all methods")