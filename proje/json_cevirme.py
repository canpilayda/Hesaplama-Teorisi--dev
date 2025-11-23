import fitz # PyMuPDF
import json
import os
import re
from PIL import Image
import pytesseract
import sys
from time import time
def json_cleaner():
    
# ====== AYARLAR ======
    KAYNAK_KLASORU = "denemepdf"  # PDF dosyalarını buraya at
    CIKTI_KLASORU = "denemecikti" # Temiz JSONL dosyaları buraya çıkacak
# ---------------------

# !!! KRİTİK: TESSERACT YOLU BURADA ZORLA TANIMLANIYOR !!!
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# -----------------------------------------------------------


    def metin_temizle(metin):
   
    # 1. Hatalı bölünen kelimeleri birleştirme
    # Satır sonundaki tireyi, boşlukları ve yeni satırı kaldırır, kelimeleri birleştirir.
     metin = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', metin)
    
    # 2. Genel satır sonlarını ve fazla boşlukları tek boşluğa indirgeme
    metin = metin.replace('\n', ' ').replace('\r', '')
    metin = re.sub(r'\s+', ' ', metin).strip()
    
    return metin

def pdf_isleyici_tam(pdf_path, cikti_jsonl_yolu):
    """
    PDF dosyasını işler. Seçilebilir metin varsa onu, yoksa OCR ile metni çeker 
    ve temizlenmiş metinleri JSONL olarak kaydeder.
    """
    
    try:
        doc = fitz.open(pdf_path)
        temizlenmis_bloklar = []
        
        print(f"'{os.path.basename(pdf_path)}' işleniyor... Toplam {doc.page_count} sayfa.")

        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            
            # 1. YÖNTEM: Seçilebilir metin çıkarma
            metin = page.get_text("text")
            
            # 2. YÖNTEM: Metin yoksa (taranmış PDF'ler) OCR dene
            if len(metin.strip()) < 10: 
                print(f"   -> Sayfa {page_num+1}: Metin çok az. OCR deneniyor...")
                
                # Sayfayı yüksek çözünürlükte resme dönüştür (2x zoom)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                temp_img_path = f"temp_page_{os.getpid()}_{page_num}.png" 
                pix.save(temp_img_path)
                
                metin = pytesseract.image_to_string(Image.open(temp_img_path), lang='eng') 
                os.remove(temp_img_path) 
                
                if len(metin.strip()) < 10:
                    print(f"   -> Sayfa {page_num+1}: OCR başarısız/boş sayfa. Atlanıyor.")
                    continue
                else:
                    print(f"   -> Sayfa {page_num+1}: OCR başarılı.")

            # Metni temizle ve AI için hazırla
            temiz_metin = metin_temizle(metin)
            
            if temiz_metin:
                # Veriyi AI eğitimi için JSONL formatında bir satır olarak hazırlıyoruz
                temizlenmis_bloklar.append({
                    "source_file": os.path.basename(pdf_path),
                    "page_num": page_num + 1,
                    "text": temiz_metin
                })

        # Tüm temizlenmiş sayfaları JSONL dosyasına yaz
        if temizlenmis_bloklar:
            with open(cikti_jsonl_yolu, "w", encoding="utf-8") as f:
                for item in temizlenmis_bloklar:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
            print(f"-> ✅ Başarılı: '{os.path.basename(cikti_jsonl_yolu)}' (JSONL) dosyası oluşturuldu.\n")
        else:
             print(f"!! ⚠️ UYARI: '{os.path.basename(pdf_path)}' dosyasından geçerli metin çıkarılamadı. JSONL oluşturulmadı.\n")


    except pytesseract.TesseractNotFoundError:
        print("\n!! ❌ KRİTİK HATA: Tesseract motoru, belirtilen yolda bulunamadı!")
        print("!! Lütfen kodun başındaki yolu kontrol edin.\n")
    except Exception as e:
        print(f"!! ❌ HATA: '{os.path.basename(pdf_path)}' işlenirken genel bir sorun oluştu: {e}\n")


# --- ANA PROGRAM ---
if __name__ == "__main__":
    start_time = time()
    
    os.makedirs(CIKTI_KLASORU, exist_ok=True)
    os.makedirs(KAYNAK_KLASORU, exist_ok=True)

    pdf_dosyalari = [f for f in os.listdir(KAYNAK_KLASORU) if f.lower().endswith(".pdf")]

    if not pdf_dosyalari:
        print(f"UYARI: '{KAYNAK_KLASORU}' klasöründe hiç PDF dosyası bulunamadı.")
    else:
        for pdf_dosya in pdf_dosyalari:
            pdf_yolu = os.path.join(KAYNAK_KLASORU, pdf_dosya)
            jsonl_yolu = os.path.join(CIKTI_KLASORU, pdf_dosya.replace(".pdf", ".jsonl", 1))
            pdf_isleyici_tam(pdf_yolu, jsonl_yolu)
            
    end_time = time()
    print("---")
    print("Tüm PDF'ler işlendi. İlk Aşama Tamamlandı! 🔥")
    print(f"Toplam süre: {end_time - start_time:.2f} saniye.")
