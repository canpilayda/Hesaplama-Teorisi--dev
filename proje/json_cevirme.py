import fitz  # PyMuPDF
import json
import os

# ====== AYARLAR ======
PDF_FOLDER = "pdfler"
JSON_FOLDER = "json_cikti"

# Çıktı klasörünü oluştur (yoksa)
os.makedirs(JSON_FOLDER, exist_ok=True)

# ====== PDF'leri JSON'a Çevir ======
for pdf_file in os.listdir(PDF_FOLDER):
    if not pdf_file.endswith(".pdf"):
        continue

    pdf_path = os.path.join(PDF_FOLDER, pdf_file)
    doc = fitz.open(pdf_path)

    pages_text = []
    for page in doc:
        text = page.get_text()
        pages_text.append(text)

    json_data = {
        "dosya_adi": pdf_file,
        "sayfa_sayisi": len(doc),
        "icerik": pages_text
    }

    json_file_name = os.path.splitext(pdf_file)[0] + ".json"
    json_path = os.path.join(JSON_FOLDER, json_file_name)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)

    print(f"[✅] {pdf_file} JSON'a çevrildi.")

print("✨ Tüm PDF’ler JSON’a dönüştürüldü!")
