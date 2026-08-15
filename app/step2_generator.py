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

    raise ValueError("Could not parse JSON dictionary from response.")

def load_file_content(filepath: str, label: str) -> str:
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                print(f"Loaded {label} from '{filepath}'...")
                return content
    return ""

def generate_lesson_plan(analysis_json_path: str) -> dict:
    with open(analysis_json_path, "r", encoding="utf-8") as f:
        analysis_data = json.load(f)

    if isinstance(analysis_data, str):
        analysis_data = json.loads(analysis_data)

    game_bank = load_file_content(GAME_BANK_FILE, "QKids Game Bank")
    user_feedback = load_file_content(FEEDBACK_FILE, "Custom Teacher Rules")

    story_analysis = analysis_data.get("story_analysis", {}) if isinstance(analysis_data, dict) else {}
    book_genre = story_analysis.get("book_genre", "Narrative Story")
    print(f"Generating lesson plan for classified genre: [{book_genre}]...")
    print("Generating QKids lesson with MANDATORY fill-in-the-blank retelling scaffolds...")

    system_instruction = f"""
    You are an expert ESL Picture Book Curriculum Designer for QKids (online 1-on-1 lessons for ~10yo students in China).
    Your task is to take the provided Book Analysis JSON and create an accurate, 25-minute ESL lesson plan.

    CLASSIFIED BOOK GENRE FOR THIS LESSON: [{book_genre}]

    PEDAGOGICAL RULES BASED ON CLASSIFIED GENRE:
    1. IF GENRE IS "Non-Fiction / Science" OR "Daily Routine / Activity":
       - Focus heavily on VOCABULARY ELABORATION & PICTURE EXTRACTION.
       - Ask "What do you need when you [action]?" to introduce related gear/equipment.
       - Identify typical sentence structures and DRILL THEM in Grammar and Games!
    2. IF GENRE IS "Narrative Story":
       - Focus on story plot, character feelings, and cause/effect reasoning.

    CRITICAL PEDAGOGY RULES:
    MANDATORY RETELLING SCAFFOLDING FORMAT (NON-NEGOTIABLE):
    - 'story_retelling' lines MUST NEVER BE FULL UNBLANKED SENTENCES!
    - Every single retelling line MUST contain blank underlines ______ AND parenthetical answer keys at the end.
    - Exact Formatting Pattern Required:
      * "First, Bert and Beth ______ to the ______ on a sunny day. (went; beach)"
      * "Then, they ______ their shadows ______ them everywhere. (noticed; following)"
      * "Next, they ______ a race and ______ over rocks. (had; jumped)"
      * "After that, they ______ silly tricks to ______ their shadows. (did; catch)"
      * "Finally, Grandfather ______ them to ______ in the shade. (told; rest)"

    CRITICAL PEDAGOGY RULES:
    1. >= 5 QUESTIONS PER PAGE MANDATORY (80% CONTENT / 20% ELABORATION):
       - Every page in 'pages' MUST contain AT LEAST 5 distinct questions.
       - 80% Content-Based Questions (4 out of 5 Qs): Visual observation, story plot comprehension, character feelings/actions directly on Page N.
       - 20% Elaboration / Open-Ended Questions (1 out of 5 Qs): Personal connection, real-world knowledge.

    2. LEVEL-APPROPRIATE VOCABULARY FOR 10YO ESL LEARNERS (A1/A2):
       - Questions and answers MUST use simple, everyday English.
       - AVOID overly complex/academic terms like "produce section" or "department".

    3. DIRECT & NATURAL COVER QUESTIONS:
       - Ask cover questions in the most direct way (e.g. "What's the title of the book?").

    4. CONDITIONAL SCENARIO ELABORATION ("What do you need...?"):
       - Apply "What do you need when..." ONLY when the page depicts a significant scenario (swimming, riding a bike, cooking). Do NOT force it on minor pages.

    5. ZERO-TYPING QKIDS GAMES — VARIED AND BOOK-SPECIFIC:
       - Select 2 games from this Game Bank (no live-typing games):
         {game_bank}
       - Pick your 2 games from 2 DIFFERENT categories in the bank (Vocabulary / Grammar & Sentence / Phonics / Picture Book Thinking) rather than defaulting to the same category or the same games every time.
       - Favor ⭐⭐⭐⭐⭐ games when they fit the book, but the actual fit to this specific story matters more than the star rating.
       - Fill in each game's "Teacher says" and "Student output" using this book's actual vocabulary, objects, or story events — follow the bank's own example format (e.g. "It is a [boot]." becomes a real object from this page) rather than leaving it generic.
       - For each of the 2 chosen games, generate at least 3 concrete, ready-to-use rounds in an "examples" field — actual on-screen content built from THIS book's vocabulary and pages, ready to display in class with no further work needed. Never output a description of what a round should contain — output the round itself. Match the format to the game type:
         * Sentence Builder: scrambled word chunks shown as pipe-separated tokens in SCRAMBLED (non-grammatical) order, e.g. "eating | The | is | dog | meat", plus the correct answer sentence.
         * Mystery Box / What's Missing?: the hidden/missing item plus the reveal order or the full item set shown.
         * Two Truths and a Lie: 3 statements about the page (2 true, 1 false) plus which one is the lie.
         * Prediction Box / Best Choice: the 3 A/B/C options shown plus a sample justified answer.
         * Any other game type: the actual on-screen content needed to run that round, in that game's own format from the bank.

    6. NO "MAKE A SENTENCE" QUESTIONS ON PAGES.
    7. NO LETTER-COUNTING OR REPETITIVE VOCABULARY MEANINGS.
    8. STRICT TENSE CONSISTENCY: Story comprehension questions MUST match story tense.
    9. QUESTION DIRECTNESS: Questions on Page N MUST ONLY ask about Page N. NO 'Looking back at page X' questions!

    CUSTOM TEACHER RULES & FEEDBACK:
    {user_feedback}

    TIMING & STRUCTURE:
    - Part 1: Greeting & Warm-up (0:00–3:00) — Cover
    - Part 2: Reading (3:00–20:00) — Page-by-page
    - Part 3: Game & Wrap-up (20:00–25:00) — Games + Retelling

    NO FORBIDDEN ITEMS:
    - NO Chinese, NO homework, NO worksheets.
    """

    prompt = f"""
    Here is the Book Analysis for the lesson:
    {json.dumps(analysis_data, indent=2)}

    Generate the complete lesson plan adhering strictly to this JSON structure:

    {{
      "book_title": "String",
      "level": "Beginner / Elementary",
      "duration": "25 minutes",
      "teaching_intention": {{
        "story_summary": "String",
        "language_goal": "String",
        "vocabulary_goal": "String",
        "thinking_goal": "String"
      }},
      "cover": {{
        "questions": [
          {{"question": "What's the title of the book?", "answer": "String"}},
          {{"question": "String", "answer": "String"}}
        ],
        "vocabulary": [
          {{"word": "String", "meaning": "String"}}
        ]
      }},
      "pages": [
        {{
          "page_number": 1,
          "story_quote": "Exact quote from page text",
          "questions": [
            {{"question": "Content Q1: Visual observation question?", "answer": "String"}},
            {{"question": "Content Q2: Story comprehension question?", "answer": "String"}},
            {{"question": "Content Q3: Character action/feelings question?", "answer": "String"}},
            {{"question": "Content Q4: Story detail question?", "answer": "String"}},
            {{"question": "Elaboration Q1: Real-world or personal connection question?", "answer": "String"}}
          ],
          "vocabulary": [
            {{"word": "String", "meaning": "Interactive guiding explanation"}}
          ]
        }}
      ],
      "grammar_focus": {{
        "grammar_point": "String",
        "story_example": "String",
        "student_sentence_frame": "String",
        "other_matching_words_in_story": "String"
      }},
      "games": [
        {{
          "game_type": "Mystery Box / Magic Cover",
          "purpose": "comprehension + speaking",
          "target_language": "Target frame",
          "screen_setup": [
            "Show image covered by digital boxes"
          ],
          "teacher_says": "What is hidden here?",
          "student_output": "Full sentence response",
          "examples": [
            {{"round": "1", "content": "Hidden item: backpack. Reveal order: strap, buckle, whole bag.", "answer": "It is a backpack."}},
            {{"round": "2", "content": "Hidden item: book. Reveal order: corner, spine, whole book.", "answer": "It is a book."}},
            {{"round": "3", "content": "Hidden item: teacher's desk. Reveal order: leg, drawer, whole desk.", "answer": "It is a desk."}}
          ]
        }},
        {{
          "game_type": "Sentence Builder",
          "purpose": "grammar + syntax",
          "target_language": "Target frame",
          "screen_setup": [
            "Show scrambled word blocks"
          ],
          "teacher_says": "Put the words in order!",
          "student_output": "Full sentence response",
          "examples": [
            {{"round": "1", "scrambled": "eating | The | is | dog | meat", "answer": "The dog is eating meat."}},
            {{"round": "2", "scrambled": "school | to | the children | walk", "answer": "The children walk to school."}},
            {{"round": "3", "scrambled": "at us | smiles | our teacher", "answer": "Our teacher smiles at us."}}
          ]
        }}
      ],
      "story_retelling": [
        "First, Bert and Beth ______ to the ______ on a sunny day. (went; beach)",
        "Then, they ______ their shadows ______ them everywhere. (noticed; following)",
        "Next, they ______ a race and ______ over rocks. (had; jumped)",
        "After that, they ______ silly tricks to ______ their shadows. (did; catch)",
        "Finally, Grandfather ______ them to ______ in the shade. (told; rest)"
      ]
    }}

    Respond ONLY with valid JSON. Do not leave blank or empty strings.
    MANDATORY: Every retelling line MUST contain blank underlines ______ AND parenthetical answers (word1; word2) at the end. NEVER output full unblanked sentences.
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

    raise RuntimeError("Failed to connect to Gemini after 3 attempts.")