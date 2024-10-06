import wikipedia
from urllib.parse import unquote, urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
import requests
from bs4 import BeautifulSoup
import time


def read_wiki_entry(url, max_chars: int | None = None):
    """
    Reads the summary of a Wikipedia entry from the given URL.
    Parameters:
        url (str): The URL of the Wikipedia page.
        max_chars (int, optional): Maximum number of characters to return.
    Returns:
        dict: A dictionary containing the success status, content, URL, and any error.
    """
    try:
        # Extract the page title from the URL
        parsed_url = urlparse(url)
        page_title = unquote(parsed_url.path.split("/")[-1])

        # Use Wikipedia API to get the page content
        page = wikipedia.page(page_title, auto_suggest=False)

        return {
            "success": True,
            "content": page.summary[:max_chars] if max_chars else page.summary,
            "url": page.url,
            "error": None,
        }
    except wikipedia.exceptions.DisambiguationError as e:
        return {
            "success": False,
            "content": None,
            "error": f"DisambiguationError: {str(e)}",
        }
    except wikipedia.exceptions.PageError as e:
        return {"success": False, "content": None, "error": f"PageError: {str(e)}"}
    except Exception as e:
        return {
            "success": False,
            "content": None,
            "error": f"Unexpected error: {str(e)}",
        }


def read_youtube_transcript(url):
    """
    Retrieves the transcript of a YouTube video from the given URL.
    Parameters:
        url (str): The URL of the YouTube video.
    Returns:
        dict: A dictionary containing the success status, transcript content, URL, and any error.
    """
    try:
        parsed_url = urlparse(url)
        video_id = (
            parse_qs(parsed_url.query).get("v", [None])[0]
            or parsed_url.path.split("/")[-1]
        )
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([entry["text"] for entry in transcript])
        return {
            "success": True,
            "content": transcript_text,
            "url": url,
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "content": None,
            "error": f"Error fetching transcript: {str(e)}",
        }


def read_webpage_content(url, max_chars: int | None = None):
    """
    Fetches and extracts the text content from a webpage.
    Parameters:
        url (str): The URL of the webpage.
        max_chars (int, optional): Maximum number of characters to return.
    Returns:
        dict: A dictionary containing the success status, content, URL, and any error.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            " AppleWebKit/537.36 (KHTML, like Gecko)"
            " Chrome/91.0.4472.124 Safari/537.36"
        )
    }
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()  # Raise an HTTPError for bad responses

            soup = BeautifulSoup(response.content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Extract text
            text = soup.get_text(separator="\n", strip=True)

            # Basic text cleaning
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = "\n".join(chunk for chunk in chunks if chunk)

            return {
                "success": True,
                "content": text[:max_chars] if max_chars else text,
                "url": url,
                "error": None,
            }

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                return {
                    "success": False,
                    "content": None,
                    "error": f"Access forbidden (403). The website may be blocking automated access: {url}",
                }
            else:
                return {
                    "success": False,
                    "content": None,
                    "error": f"HTTP Error: {e}",
                }
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return {
                "success": False,
                "content": None,
                "error": f"Failed to fetch the webpage after {max_retries} attempts: {e}",
            }

    return {
        "success": False,
        "content": None,
        "error": f"Failed to fetch the webpage after {max_retries} attempts due to unknown reasons.",
    }


AVAILABLE_ACTIONS = {
    "read_wiki_entry": {
        "function": read_wiki_entry,
        "description": "Reads the summary of a Wikipedia entry from a given Wikipedia URL.",
    },
    "read_youtube_transcript": {
        "function": read_youtube_transcript,
        "description": "Retrieves the transcript of a YouTube video from a given YouTube URL. Applicable only to YouTube links.",
    },
    "read_webpage_content": {
        "function": read_webpage_content,
        "description": "Fetches and extracts the text content from a webpage URL.",
    },
}
