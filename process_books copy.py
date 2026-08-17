import os
import json
import time
from app.step0_loader import load_book
from app.step1_analyzer import analyze_picture_book
from app.step2_generator import generate_lesson_plan
from app.step3_critic import audit_and_revise_lesson
from app.step4_docx_builder import build_docx_from_json

BOOKS_DIR = "books"
OUTPUT_DIR = "output_lessons"
TEMP_ANALYSIS = "temp_analysis.json"
TEMP_LESSON = "temp_lesson.json"

def scan_book_targets(books_dir: str) -> list:
    targets = []
    if not os.path.exists(books_dir):
        return targets

    for root, dirs, files in os.walk(books_dir):
        if os.path.basename(root).startswith(".") or os.path.basename(root).startswith("temp_"):
            continue

        image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        pdf_files = [f for f in files if f.lower().endswith('.pdf') and not f.startswith("temp_")]

        if image_files:
            targets.append(root)
        
        for pdf in pdf_files:
            targets.append(os.path.join(root, pdf))

    return targets

def process_all_books():
    os.makedirs(BOOKS_DIR, exist_ok=True)
    os.makedirs(os.path.join(BOOKS_DIR, "PDF"), exist_ok=True)
    os.makedirs(os.path.join(BOOKS_DIR, "Images"), exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    targets = scan_book_targets(BOOKS_DIR)

    if not targets:
        print(f"No PDFs or image folders found inside '{BOOKS_DIR}/'.")
        return

    print(f"==================================================")
    print(f"FOUND {len(targets)} BOOK(S) TO PROCESS IN BATCH")
    print(f"==================================================\n")

    for idx, target_path in enumerate(targets, 1):
        target_name = os.path.basename(target_path)
        print(f"--------------------------------------------------")
        print(f"[{idx}/{len(targets)}] PROCESSING: {target_name}")
        print(f"--------------------------------------------------")

        try:
            # Step 0: Load Book
            book_package = load_book(target_path)
            book_title = book_package["book_title"]
            output_docx = os.path.join(OUTPUT_DIR, f"{book_title}_Lesson_Plan.docx")

            # Step 1: Book Analysis
            analysis_data = analyze_picture_book(book_package)
            with open(TEMP_ANALYSIS, "w", encoding="utf-8") as f:
                json.dump(analysis_data, f, indent=2)

            # Step 2: Lesson Generation
            draft_lesson = generate_lesson_plan(TEMP_ANALYSIS)
            with open(TEMP_LESSON, "w", encoding="utf-8") as f:
                json.dump(draft_lesson, f, indent=2)

            # Step 3: Critic Audit
            audit_result = audit_and_revise_lesson(TEMP_LESSON)
            revised_lesson = {}
            if isinstance(audit_result, dict):
                revised_lesson = audit_result.get("revised_lesson", {})
                if isinstance(revised_lesson, str):
                    try:
                        revised_lesson = json.loads(revised_lesson)
                    except Exception:
                        revised_lesson = draft_lesson

            if revised_lesson and isinstance(revised_lesson, dict):
                with open(TEMP_LESSON, "w", encoding="utf-8") as f:
                    json.dump(revised_lesson, f, indent=2)

            # Step 4: Build DOCX
            build_docx_from_json(TEMP_LESSON, output_docx)
            print(f"✅ FINISHED! Saved to: '{output_docx}'\n")

            if book_package["source_type"] == "image" and os.path.exists(book_package["pdf_path"]):
                os.remove(book_package["pdf_path"])

        except Exception as e:
            print(f"❌ ERROR processing '{target_name}': {e}\n")

        time.sleep(2)

    for temp in [TEMP_ANALYSIS, TEMP_LESSON]:
        if os.path.exists(temp):
            os.remove(temp)

    print("==================================================")
    print("🎉 ALL BOOKS PROCESSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    process_all_books()