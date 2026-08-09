import os
import glob
from PIL import Image

def sanitize_path(path: str) -> str:
    """Fixes non-breaking spaces (\xa0) and web-copied space glitches in filenames."""
    if '\xa0' in path or '\u00a0' in path:
        clean_path = path.replace('\xa0', ' ').replace('\u00a0', ' ')
        if os.path.exists(path) and not os.path.exists(clean_path):
            try:
                os.rename(path, clean_path)
                print(f"Renamed web space in filename to clean space: '{clean_path}'")
                return clean_path
            except Exception:
                pass
    return path

def get_file_creation_time(filepath: str) -> float:
    stat = os.stat(filepath)
    try:
        return stat.st_birthtime
    except AttributeError:
        return stat.st_mtime

def load_book(target_path: str) -> dict:
    target_path = sanitize_path(target_path)
    
    if not os.path.exists(target_path):
        raise FileNotFoundError(f"Target path '{target_path}' does not exist.")

    if os.path.isfile(target_path) and target_path.lower().endswith(".pdf"):
        book_title = os.path.splitext(os.path.basename(target_path))[0]
        return {
            "book_title": book_title,
            "source_type": "pdf",
            "pdf_path": target_path,
            "pages": []
        }
    elif os.path.isdir(target_path):
        book_title = os.path.basename(target_path.rstrip("/\\"))
        valid_extensions = ("*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG", "*.JPEG")
        
        image_paths = []
        for ext in valid_extensions:
            image_paths.extend(glob.glob(os.path.join(target_path, ext)))

        if not image_paths:
            raise ValueError(f"No image files found inside folder '{target_path}'.")

        image_paths.sort(key=get_file_creation_time)
        pages = [{"page_number": idx, "image_path": p} for idx, p in enumerate(image_paths, 1)]

        print(f"[{book_title}] Stitching {len(pages)} screenshot pages into temporary PDF...")
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
        raise ValueError(f"Invalid target path: '{target_path}'.")