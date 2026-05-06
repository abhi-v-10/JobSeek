import io
import fitz  # PyMuPDF
from PIL import Image
import base64

def extract_text_from_file(file_content: bytes, filename: str) -> str:
    """
    Extract text from various file types.
    Supports .pdf, .txt, .docx (basic), and images (via vision later).
    """
    ext = filename.split(".")[-1].lower()
    
    if ext == "pdf":
        doc = fitz.open(stream=file_content, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    
    if ext in ["txt", "md"]:
        return file_content.decode("utf-8", errors="ignore")
    
    # docx extraction would need python-docx, skipping for now or adding later
    return ""

def encode_image(image_content: bytes) -> str:
    """Encode image to base64 for OpenAI Vision."""
    return base64.b64encode(image_content).decode('utf-8')
