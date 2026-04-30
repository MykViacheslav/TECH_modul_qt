import os
import sys
from pypdf import PdfReader
import json

# Ensure stdout handles utf-8
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def extract_text_from_pdf(path):
    try:
        reader = PdfReader(path)
        text = ""
        # Only first 2 pages
        for i in range(min(len(reader.pages), 2)):
            text += reader.pages[i].extract_text() + "\n--- PAGE BREAK ---\n"
        return text
    except Exception as e:
        return f"Error: {str(e)}"

folders = [
    r"C:\pythonproject\tech_modul\faktury",
    r"C:\Users\mykyt\Downloads"
]

results = []

for folder in folders:
    if not os.path.exists(folder):
        continue
    files = [f for f in os.listdir(folder) if f.lower().endswith(".pdf")]
    # Limit to 5 files to avoid overload
    for f in files[:5]:
        path = os.path.join(folder, f)
        results.append({
            "folder": folder,
            "filename": f,
            "content": extract_text_from_pdf(path)
        })

print(json.dumps(results, indent=2, ensure_ascii=False))
