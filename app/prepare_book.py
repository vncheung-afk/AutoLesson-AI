import os
import shutil
import fitz


BOOK_FOLDER = "books"
KNOWLEDGE_FOLDER = "knowledge"
PACKAGE_FOLDER = "upload_package"


def find_books():
    return [
        file for file in os.listdir(BOOK_FOLDER)
        if file.lower().endswith(".pdf")
    ]


def clean_name(filename):
    return filename.replace(".pdf", "").replace(" ", "_")


def create_package(book):

    book_name = clean_name(book)

    output_folder = os.path.join(
        PACKAGE_FOLDER,
        book_name
    )

    os.makedirs(output_folder, exist_ok=True)

    print(f"\nPreparing: {book}")

    # 1. Extract pages as images
    pdf_path = os.path.join(
        BOOK_FOLDER,
        book
    )

    doc = fitz.open(pdf_path)

    image_folder = os.path.join(
        output_folder,
        "pages"
    )

    os.makedirs(image_folder, exist_ok=True)

    for i, page in enumerate(doc):

        pix = page.get_pixmap(dpi=200)

        image_path = os.path.join(
            image_folder,
            f"page_{i+1}.png"
        )

        pix.save(image_path)

        print("Saved:", image_path)


    # 2. Copy Teacher Brain
    shutil.copy(
        os.path.join(
            KNOWLEDGE_FOLDER,
            "ESL_Picture_Book_Lesson_System_v1.2.docx"
        ),
        output_folder
    )


    # 3. Copy Lesson Template
    shutil.copy(
        os.path.join(
            KNOWLEDGE_FOLDER,
            "ESL_Picture_Book_Lesson_Template_v1.docx"
        ),
        output_folder
    )


    # 4. Copy Quality Example
    shutil.copy(
        os.path.join(
            KNOWLEDGE_FOLDER,
            "Kitty_Cat_and_the_Frog_Lesson_Plan.docx"
        ),
        output_folder
    )


    # 5. Create instruction file
    instruction = """
Create a 25-minute ESL picture book lesson plan.

Use:
- ESL Picture Book Lesson System v1.2
- ESL Picture Book Lesson Template v1
- Kitty Cat and the Frog Lesson Plan as a quality reference

Analyze:
- story content
- illustrations
- teaching goals

Include:
- teaching intention analysis
- cover questions
- page-by-page questions
- vocabulary
- grammar focus
- speaking games
- story retelling

Follow the formatting rules.

The lesson should be teacher-ready,
interactive, student-centered,
and similar in quality and depth
to the Kitty Cat and the Frog example.
"""

    with open(
        os.path.join(output_folder, "instructions.txt"),
        "w",
        encoding="utf-8"
    ) as f:
        f.write(instruction)


    print("\nPackage ready:", output_folder)



if __name__ == "__main__":

    os.makedirs(PACKAGE_FOLDER, exist_ok=True)

    books = find_books()

    for book in books:
        create_package(book)