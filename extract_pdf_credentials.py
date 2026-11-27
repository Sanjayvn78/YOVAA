from pathlib import Path
from pypdf import PdfReader

pdf_path = Path("c:/Users/Sanjay/Downloads/YOVAA_Admin_Login_Credentials.pdf")
print(f"exists: {pdf_path.exists()}")
if not pdf_path.exists():
    raise SystemExit(1)

reader = PdfReader(str(pdf_path))
for i, page in enumerate(reader.pages, 1):
    text = page.extract_text() or ""
    print(f"--- PAGE {i} ---")
    print(text)
