import os
import json
import time
import re
from dotenv import load_dotenv
from google import genai
from google.genai import types
from json_repair import repair_json

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file!")

client = genai.Client(api_key=api_key)

def clean_and_parse_json(text) -> dict:
    if not text:
        raise ValueError("Received empty response from Gemini.")
    if isinstance(text, dict):
        return text
    if isinstance(text, list) and len(text) > 0 and isinstance(text[0], dict):
        return text[0]

    raw_str = str(text).strip()

    try:
        repaired = repair_json(raw_str, return_objects=True)
        if isinstance(repaired, dict):
            return repaired
        if isinstance(repaired, list) and len(repaired) > 0 and isinstance(repaired[0], dict):
            return repaired[0]
        if isinstance(repaired, str):
            d = json.loads(repaired)
            if isinstance(d, dict):
                return d
    except Exception:
        pass

    cleaned = re.sub(r'^```(?:json)?\s*', '', raw_str, flags=re.MULTILINE)
    cleaned = re.sub(r'```$', '', cleaned.strip(), flags=re.MULTILINE)
    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if match:
        try:
            d = json.loads(match.group(0))
            if isinstance(d, dict):
                return d
        except Exception:
            pass

    raise ValueError(f"Could not parse JSON dictionary from response: {raw_str[:150]}...")

def analyze_picture_book(book_package: dict) -> dict:
    pdf_path = book_package["pdf_path"]
    book_title = book_package["book_title"]

    print(f"[{book_title}] Uploading to Gemini File API...")
    uploaded_file = client.files.upload(file=pdf_path)
    print(f"[{book_title}] Upload complete. Extracting exact quotes and language features...")

    system_instruction = """
You are an expert ESL Picture Book Curriculum Designer.
Your task is to analyze the attached picture book PDF, classify its book genre, and extract EXACT page quotes and visual details.
You must NOT invent or rephrase story text. Copy exact text from each page.
"""

    prompt = """
    Perform a complete 'Picture Book Analysis' on this PDF using the following JSON structure:

    {
      "basic_information": {
        "book_title": "String",
        "estimated_reading_difficulty": "String",
        "main_characters": ["String"]
      },
       "story_analysis": {
        "book_genre": "Narrative Story OR Non-Fiction / Science OR Daily Routine / Activity",
        "original_story_tense": "Past Tense OR Present Tense",
        "short_summary": "3-5 sentences summary",
        "pages_breakdown": [
          {
            "page_number": 2,
            "exact_story_text": "Exact quote from page 2 of the PDF",
            "visual_details": "Description of what is in the picture on page 2"
          }
        ]
      },
      "language_feature_analysis": {
        "ranked_teaching_priorities": [
          {
            "rank": 1,
            "feature": "String (e.g. Rhyming words, Phonics, Grammar)",
            "reason": "Why this is rank 1"
          }
        ],
        "phonics_and_sound_features": {
          "rhyming_words": ["String"],
          "sound_patterns": ["String"]
        },
        "vocabulary_analysis": {
          "core_vocabulary": ["String"]
        }
      },
      "grammar_focus": {
        "feature": "String",
        "story_examples": ["String"]
      }
    }

    OUTPUT RULES:
    1. Respond ONLY with valid JSON.
    2. Classify book_genre accurately as "Narrative Story", "Non-Fiction / Science", or "Daily Routine / Activity".
    3. Ensure exact_story_text contains the exact verbatim text printed on each page.
    """

    try:
        for attempt in range(1, 4):
            try:
                response = client.models.generate_content(
                    model="gemini-flash-lite-latest",
                    contents=[uploaded_file, prompt],
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json"
                    )
                )
                return clean_and_parse_json(response.text)
            except Exception as e:
                if "503" in str(e) or "UNAVAILABLE" in str(e):
                    print(f"Google Server Busy (503). Retrying in 3 seconds... (Attempt {attempt}/3)")
                    time.sleep(3)
                else:
                    raise e
        raise RuntimeError("Failed to connect to Gemini after 3 attempts.")
    finally:
        try:
            client.files.delete(name=uploaded_file.name)
        except Exception:
            pass