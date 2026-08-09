import os


PACKAGE_FOLDER = "upload_package"


def find_packages():

    return [
        folder
        for folder in os.listdir(PACKAGE_FOLDER)
        if os.path.isdir(
            os.path.join(PACKAGE_FOLDER, folder)
        )
    ]


def create_prompt(package_name):

    package_path = os.path.join(
        PACKAGE_FOLDER,
        package_name
    )

    prompt = f"""
You are an experienced ESL picture book teacher and curriculum designer.

Create a high-quality 25-minute ESL picture book lesson plan.

Book package location:
{package_path}

Use the following references:

1. ESL Picture Book Lesson System v1.2
Follow all teaching principles and generation rules.

2. ESL Picture Book Lesson Template v1
Follow the lesson structure and formatting requirements.

3. Kitty Cat and the Frog Lesson Plan
Use this as the quality and depth reference.

Lesson requirements:

Include:
- teaching intention analysis
- story summary
- language goals
- vocabulary goals
- thinking goals
- warm-up
- cover discussion
- page-by-page reading questions
- vocabulary
- sentence frames
- grammar focus
- speaking games
- story retelling

The lesson should:
- be suitable for a 25-minute QKids lesson
- encourage student speaking
- be practical for teachers to use immediately
- focus on language production

Do not include:
- homework
- worksheets
- Chinese translations
- assessment sections

Output:
Only JSON.

The JSON must follow:
schemas/Lesson_Schema_v1.json
"""

    output_file = os.path.join(
        package_path,
        "AI_prompt.txt"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(prompt)

    print("Created:", output_file)


if __name__ == "__main__":

    packages = find_packages()

    for package in packages:
        create_prompt(package)