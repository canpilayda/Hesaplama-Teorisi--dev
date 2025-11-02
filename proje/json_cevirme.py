import fitz # PyMuPDF
import json
import os
import re
import sys

# ====== AYARLAR ======
KAYNAK_KLASORU = "pdfler"  # PDF dosyalarını buraya at
CIKTI_KLASORU = "json_cikti" # Temiz JSONL dosyaları buraya çıkacak
# ---------------------

def metin_temizle(metin):
    """
    AI eğitimi için kritik olan satır sonu ve tireleme hatalarını düzeltir
    ve genel temizliği yapar.
    """
    
    # 1. Hatalı bölünen kelimeleri birleştirme (Örn: 'odevim-\niz' -> 'odevimiz')
    # Satır sonundaki tireyi ve yeni satırı kaldırır, kelimeleri birleştirir.
    metin = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', metin)
    
    # 2. Genel satır sonlarını ve fazla boşlukları temizleme
    metin = metin.replace('\n', ' ').replace('\r', '')
    
    # 3. Birden fazla boşluğu tek boşluğa indirgeme
    metin = re.sub(r'\s+', ' ', metin).strip()
    
    return metin

def pdf_isleyici_basit(pdf_path, cikti_jsonl_yolu):
    """PDF dosyasını işler, SADECE seçilebilir metni çeker ve temiz JSONL çıktısı verir."""
    
    try:
        doc = fitz.open(pdf_path)
        temizlenmis_bloklar = []
        
        print(f"'{os.path.basename(pdf_path)}' işleniyor... Toplam {doc.page_count} sayfa.")

        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            
            # SADECE Seçilebilir metin çıkarma
            metin = page.get_text("text") 
            
            # Metni temizle
            temiz_metin = metin_temizle(metin)
            
            if len(temiz_metin) < 10:
                # Metin yoksa veya çok azsa (büyük ihtimalle taranmış/boş sayfa) atla.
                print(f"   -> Sayfa {page_num+1}: Metin çok az/yok. Atlanıyor.")
                continue

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
             print(f"!! ⚠️ UYARI: '{os.path.basename(pdf_path)}' dosyasından hiçbir metin çıkarılamadı (Tamamen taranmış olabilir). JSONL dosyası oluşturulmadı.\n")


    except Exception as e:
        print(f"!! ❌ HATA: '{os.path.basename(pdf_path)}' işlenirken genel bir sorun oluştu: {e}\n")


# --- ANA PROGRAM ---
if __name__ == "__main__":
    os.makedirs(CIKTI_KLASORU, exist_ok=True)
    os.makedirs(KAYNAK_KLASORU, exist_ok=True)

    pdf_dosyalari = [f for f in os.listdir(KAYNAK_KLASORU) if f.lower().endswith(".pdf")]

    if not pdf_dosyalari:
        print(f"UYARI: '{KAYNAK_KLASORU}' klasöründe hiç PDF dosyası bulunamadı. Lütfen PDF'leri bu klasöre atın.")
    else:
        for pdf_dosya in pdf_dosyalari:
            pdf_yolu = os.path.join(KAYNAK_KLASORU, pdf_dosya)
            # Çıktı formatı: Dosya Adı.jsonl
            jsonl_yolu = os.path.join(CIKTI_KLASORU, pdf_dosya.replace(".pdf", ".jsonl", 1))
            pdf_isleyici_basit(pdf_yolu, jsonl_yolu)
            
        print("---")
        print("Tüm PDF'ler işlendi. İlk Aşama Tamamlandı! 🔥")
        print(f"Temiz veriler '{CIKTI_KLASORU}' klasöründe seni bekliyor.")