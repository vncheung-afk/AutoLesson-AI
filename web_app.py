import os
import json
import zipfile
import tempfile
import streamlit as st

from app.step0_loader import load_book
from app.step1_analyzer import analyze_picture_book
from app.step2_generator import generate_lesson_plan
from app.step3_critic import audit_and_revise_lesson
from app.step4_docx_builder import build_docx_from_json

# Page Config
st.set_page_config(
    page_title="AutoLesson AI — Lesson Planner",
    page_icon="📚",
    layout="centered"
)

st.title("📚 AutoLesson AI")
st.subheader("AI-Powered ESL Picture Book Lesson Plan Generator")
st.markdown("Upload any picture book (PDF or ZIP folder of screenshots) to instantly generate a 25-minute Microsoft Word (.docx) lesson plan.")

# Sidebar Passcode Lock
st.sidebar.header("🔒 Access Control")
passcode_input = st.sidebar.text_input("Enter Passcode to unlock:", type="password")

# Safe Passcode Retrieval (works locally and in cloud)
try:
    PASSCODE = st.secrets.get("APP_PASSCODE", "qkids2026")
except Exception:
    PASSCODE = os.getenv("APP_PASSCODE", "qkids2026")

if passcode_input != PASSCODE:
    st.warning("🔒 Please enter the access passcode in the sidebar to unlock the generator.")
else:
    st.success("App Unlocked! You have full access.")

    uploaded_file = st.file_uploader(
        "Upload a Picture Book (PDF or ZIP file of screenshots):",
        type=["pdf", "zip"]
    )

    if uploaded_file is not None:
        book_filename = uploaded_file.name
        book_title = os.path.splitext(book_filename)[0]

        st.info(f"Target Book: **{book_filename}**")

        if st.button("🚀 Generate Lesson Plan", type="primary"):
            with tempfile.TemporaryDirectory() as temp_dir:
                input_path = os.path.join(temp_dir, book_filename)
                
                with open(input_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                target_path = input_path

                if book_filename.lower().endswith(".zip"):
                    extract_folder = os.path.join(temp_dir, book_title)
                    os.makedirs(extract_folder, exist_ok=True)
                    with zipfile.ZipFile(input_path, 'r') as zip_ref:
                        zip_ref.extractall(extract_folder)
                    target_path = extract_folder

                status = st.status("Processing Lesson Plan Pipeline...", expanded=True)
                
                try:
                    status.write("📥 **Step 0:** Ingesting book and sorting page sequence...")
                    book_package = load_book(target_path)

                    status.write("🔍 **Step 1:** Analyzing story text, rhymes, and visual details...")
                    temp_analysis_path = os.path.join(temp_dir, "temp_analysis.json")
                    analysis_data = analyze_picture_book(book_package)
                    with open(temp_analysis_path, "w", encoding="utf-8") as f:
                        json.dump(analysis_data, f, indent=2)

                    status.write("✍️ **Step 2:** Generating 25-minute QKids pedagogical lesson plan...")
                    temp_lesson_path = os.path.join(temp_dir, "temp_lesson.json")
                    draft_lesson = generate_lesson_plan(temp_analysis_path)
                    with open(temp_lesson_path, "w", encoding="utf-8") as f:
                        json.dump(draft_lesson, f, indent=2)

                    status.write("🛡️ **Step 3:** Running AI Quality Auditor (11-point rubric check)...")
                    audit_result = audit_and_revise_lesson(temp_lesson_path)
                    revised_lesson = audit_result.get("revised_lesson", draft_lesson) if isinstance(audit_result, dict) else draft_lesson
                    if isinstance(revised_lesson, dict):
                        with open(temp_lesson_path, "w", encoding="utf-8") as f:
                            json.dump(revised_lesson, f, indent=2)

                    status.write("📄 **Step 4:** Assembling 15pt Microsoft Word (.docx) document...")
                    output_docx_path = os.path.join(temp_dir, f"{book_title}_Lesson_Plan.docx")
                    build_docx_from_json(temp_lesson_path, output_docx_path)

                    status.update(label="🎉 Lesson Plan Ready!", state="complete", expanded=False)

                    with open(output_docx_path, "rb") as f:
                        docx_bytes = f.read()

                    st.balloons()
                    st.download_button(
                        label="📥 Download Microsoft Word (.docx) Lesson Plan",
                        data=docx_bytes,
                        file_name=f"{book_title}_Lesson_Plan.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )

                except Exception as e:
                    status.update(label="❌ Generation Failed", state="error")
                    st.error(f"Error during processing: {e}")