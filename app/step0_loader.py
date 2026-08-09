import os
import glob
from PIL import Image

def get_file_creation_time(filepath: str) -> float:
    """Returns file creation time (macOS/Linux compatible)."""
    stat = os.stat(filepath)
    try:
        return stat.st_birthtime  # macOS creation time
    except AttributeError:
        return stat.st_mtime      # Fallback to modification time

def load_book(target_path: str) -> dict:
    """
    Detects whether the target is a PDF or an image folder.
    Returns a standardized BookPackage dictionary.
    """
    if not os.path.exists(target_path):
        raise FileNotFoundError(f"Target path '{target_path}' does not exist.")

    # CASE A: Input is a PDF file
    if os.path.isfile(target_path) and target_path.lower().endswith(".pdf"):
        book_title = os.path.splitext(os.path.basename(target_path))[0]
        return {
            "book_title": book_title,
            "source_type": "pdf",
            "pdf_path": target_path,
            "pages": []
        }

    # CASE B: Input is a folder of screenshot images
    elif os.path.isdir(target_path):
        book_title = os.path.basename(target_path.rstrip("/\\"))
        valid_extensions = ("*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG", "*.JPEG")
        
        image_paths = []
        for ext in valid_extensions:
            image_paths.extend(glob.glob(os.path.join(target_path, ext)))

        if not image_paths:
            raise ValueError(f"No image files found inside folder '{target_path}'.")

        # REQUIREMENT: Sort pages by creation time (oldest first)
        image_paths.sort(key=get_file_creation_time)

        # Build page metadata
        pages = []
        for idx, img_path in enumerate(image_paths, 1):
            pages.append({
                "page_number": idx,
                "image_path": img_path
            })

        # Stitch images into a temporary PDF for Gemini API compatibility
        print(f"[{book_title}] Stitching {len(pages)} screenshot pages in creation-time order...")
        images = [Image.open(p["image_path"]).convert("RGB") for p in pages]
        
        temp_pdf_path = os.path.join(os.path.dirname(target_path), f"temp_{book_title}.pdf")
        images[0].save(temp_pdf_path, save_all=True, append_images=images[1:])

        return {
            "book_title": book_title,
            "source_type": "image",
            "pdf_path": temp_pdf_path,
            "pages": pages
        }

    else:
        raise ValueError(f"Invalid target path: '{target_path}'. Must be a PDF or image folder.")