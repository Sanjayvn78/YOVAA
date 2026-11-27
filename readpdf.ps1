$python = "C:/Users/Sanjay/AppData/Local/Programs/Python/Python311/python.exe"
& $python -m pip install pypdf -q
@'
from pathlib import Path
from pypdf import PdfReader
pdf_path = Path("c:/Users/Sanjay/Downloads/YOVAA_Admin_Login_Credentials.pdf")
print(f"exists: {pdf_path.exists()}")
reader = PdfReader(str(pdf_path))
for i, page in enumerate(reader.pages, 1):
    text = page.extract_text() or ""
    print(f"--- PAGE {i} ---")
    print(text[:12000])
'@ | & $python -
