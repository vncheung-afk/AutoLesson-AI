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

GAME_BANK_FILE = "knowledge/qkids_game_bank.txt"
FEEDBACK_FILE = "knowledge/user_feedback.txt"

def clean_and_parse_json(text) -> dict:
    if not text:
        return {}
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

    raise ValueError("Could not parse valid JSON dictionary from response.")

def load_file_content(filepath: str) -> str:
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                return content
    return ""

def audit_and_revise_lesson(lesson_json_path: str) -> dict:
    with open(lesson_json_path, "r", encoding="utf-8") as f:
        draft_lesson = json.load(f)

    if isinstance(draft_lesson, str):
        draft_lesson = json.loads(draft_lesson)

    game_bank = load_file_content(GAME_BANK_FILE)
    user_feedback = load_file_content(FEEDBACK_FILE)

    print("Running Quality Critic rubric audit...")

    system_instruction = f"""
    You are a Senior ESL Curriculum Auditor for QKids. Evaluate the draft lesson plan against every rubric item below.
    For ANY failure, state the issue AND return a FULLY CORRECTED revised version of the lesson plan JSON.

    CRITIC RUBRIC CHECKLIST:
    [ ] RETELLING MUST HAVE BLANKS & PARENTHESES: Every retelling line MUST contain blank underlines ______ AND parenthetical answers at the end (e.g. 'First, Bert and Beth ______ to the ______ on a sunny day. (went; beach)'). NEVER allow full unblanked sentences.
    [ ] >= 5 QUESTIONS PER PAGE (80% CONTENT / 20% ELABORATION): Every page MUST contain AT LEAST 5 questions (80% story/visual content, 20% elaboration/personal connection).
    [ ] LEVEL-APPROPRIATE VOCABULARY (A1/A2): Questions/answers use simple, everyday English. NO complex terms like 'produce section'.
    [ ] DIRECT COVER QUESTIONS: Cover asks "What's the title of the book?" in a direct, natural way.
    [ ] CONDITIONAL SCENARIO ELABORATION: Scenario elaboration ('What do you need when...?') is applied ONLY on pages with significant scenarios.
    [ ] NO MAKE A SENTENCE ON PAGES: Page questions MUST NOT ask students to 'make a sentence'.
    [ ] ZERO TYPING, VARIED, BOOK-SPECIFIC GAMES: Games use zero-typing setups from the Game Bank, drawn from 2 different bank categories, with Teacher says / Student output filled in using this book's actual content rather than generic placeholders. Flag if the same games are reused lesson after lesson instead of the best fit for this book.
    [ ] GAME EXAMPLES ARE USABLE, NOT DESCRIPTIVE: Each game has at least 3 concrete "examples" entries built from this book's real content, ready to display in class with no further work — not a generic description of the game mechanic. Sentence Builder examples must show scrambled word chunks as pipe-separated tokens in non-grammatical order (e.g. "eating | The | is | dog | meat") plus the correct answer sentence.
    [ ] NO LETTER COUNTING / NO REPETITIVE VOCAB: Vocabulary meanings MUST NOT repeat the word twice or use letter-counting.
    [ ] TENSE MATCHING: Story questions strictly match story tense.
    [ ] NO LOOKING BACK QUESTIONS: Page N questions only ask about Page N.
    [ ] SHORT & NATURAL QUESTION PHRASING: Questions are short, natural spoken English (well under 10 words where possible) — not long, exam-style, or over-describing what's already visible in the picture. Example fix: "What is on the kite in the picture?" should be "What does the kite look like?"
    [ ] PAGE NUMBERING: Cover counts as Page 1. The "pages" array starts at page_number 2 and continues sequentially — flag and fix if it starts at 1.
    [ ] QKIDS GAME BANK: Games MUST draw from the QKids Game Bank:
    {game_bank}
    [ ] TIMING BLOCKS: Divided into 3 explicit time blocks: (0:00–3:00) / (3:00–20:00) / (20:00–25:00).
    [ ] CUSTOM TEACHER RULES:
    {user_feedback}

    OUTPUT REQUIREMENT:
    Return a JSON object containing:
    1. "rubric_audit_results": Array of items checked and fixes applied.
    2. "revised_lesson": Full corrected lesson plan matching generator schema.
    """

    prompt = f"""
    Here is the draft lesson plan to audit and correct:
    {json.dumps(draft_lesson, indent=2)}

    Return ONLY a valid JSON object matching the required structure.
    """

    for attempt in range(1, 4):
        try:
            response = client.models.generate_content(
                model="gemini-flash-lite-latest",
                contents=[prompt],
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
                
    raise RuntimeError("Failed to connect to Gemini after 3 attempts due to server traffic.")


if __name__ == "__main__":
    draft_file = "test_lesson_output.json"
    if os.path.exists(draft_file):
        audit_result = audit_and_revise_lesson(draft_file)
        
        print("\n================ RUBRIC AUDIT RESULTS ================")
        for res in audit_result.get("rubric_audit_results", []):
            status = "✅ PASS" if res.get("passed") else "❌ FAIL (FIXED)"
            print(f"{status}: {res.get('item')} -> {res.get('fix_applied', 'OK')}")
        print("=====================================================\n")
            
        revised_lesson = audit_result.get("revised_lesson", {})
        with open(draft_file, "w", encoding="utf-8") as f:
            json.dump(revised_lesson, f, indent=2)
            
        print(f"SUCCESS! Audit-corrected lesson saved to '{draft_file}'.")
    else:
        print(f"ERROR: Could not find '{draft_file}'. Run step2_generator.py first.")