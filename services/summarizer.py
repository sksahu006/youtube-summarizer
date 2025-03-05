import httpx
import logging
from core.config import settings
from typing import Literal

logger = logging.getLogger(__name__)

async def summarize_text(text: str, model: Literal["gemini", "mistral"] = "gemini") -> str:
    """
    Summarize text using either Gemini or Mistral API based on the model argument.
    """
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        try:
            if model == "gemini":
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={settings.GEMINI_API_KEY}",
                    headers={"Content-Type": "application/json"},
                    json={"contents": [{"parts": [{"text": f"Summarize this and make notes of key points: {text}"}]}]}
                )
                response.raise_for_status()
                data = response.json()
                summary = data["candidates"][0]["content"]["parts"][0]["text"]
            elif model == "mistral":
                response = await client.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    json={
                        "model": "mistral-small-latest",
                        "messages": [{"role": "user", "content": f"make detailed note from this : {text}"}],
                        "max_tokens": 300
                    }
                )
                response.raise_for_status()
                data = response.json()
                summary = data["choices"][0]["message"]["content"]
            else:
                raise ValueError(f"Unsupported model: {model}")

            return summary
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("Rate limit exceeded. Returning summarized content so far.")
                return ""  # Return an empty string to signal the caller to return the accumulated summaries
            else:
                logger.error(f"HTTP error with {model}: {e.response.status_code} - {e.response.text}")
                raise
        except httpx.RequestError as e:
            logger.error(f"Request error with {model}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in summarize_text with {model}: {str(e)}")
            raise

async def summarize_transcript(transcript: str, model: Literal["gemini", "mistral"] = "gemini") -> str:
    """
    Summarize transcript in chunks using the specified model.
    """
    chunk_size = 40000 if model == "mistral" else 20000
    chunks = [transcript[i:i+chunk_size] for i in range(0, len(transcript), chunk_size)]
    summaries = []
    print(f"length of chunks: {len(transcript)}")

    for chunk in chunks:
        try:
            summary = await summarize_text(chunk, model=model)
        except Exception as e:
            logger.error(f"Error summarizing chunk: {str(e)}")
            continue
        if summary == "":
            # If an empty string is returned, it means a 429 error occurred
            break
        summaries.append(summary)

    return " ".join(summaries)
