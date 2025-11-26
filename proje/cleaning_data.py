import os
import json
import spacy
import textacy.preprocessing as tprep
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import IsolationForest

# AYARLAR
GIRIS_KLASORU = "json_cikti"   # PDF'lerden çıkan .jsonl dosyalarının bulunduğu klasör
CIKTI_KLASORU = "clean_data"  # Temizlenmiş verilerin kaydedileceği klasör
os.makedirs(GIRIS_KLASORU, exist_ok=True)
os.makedirs(CIKTI_KLASORU, exist_ok=True)

# TÜM JSONL DOSYALARINI OKU
def jsonl_dosyalarini_yukle(klasor):
    tum_veri = []
    for dosya in os.listdir(klasor):
        if dosya.endswith(".jsonl"):
            yol = os.path.join(klasor, dosya)
            with open(yol, "r", encoding="utf-8") as f:
                for satir in f:
                    try:
                        item = json.loads(satir)
                        tum_veri.append(item)
                    except json.JSONDecodeError:
                        print(f"⚠️ Uyarı: '{dosya}' içinde bozuk bir satır atlandı.")
    print(f"Toplam {len(tum_veri)} metin yüklendi ({len(os.listdir(klasor))} dosyadan).")
    return tum_veri

# METİN TEMİZLİĞİ (spaCy + Textacy)
def metin_temizle(veri):
    print("spaCy modeli yükleniyor (en_core_web_lg)...")
    nlp = spacy.load("en_core_web_lg")

    for item in veri:
        text = item["text"]
        
        # --- Textacy ile ön temizleme ---
        text = tprep.normalize_whitespace(text)
        text = tprep.remove_urls(text)
        text = tprep.remove_emails(text)
        text = tprep.remove_numbers(text)
        text = tprep.remove_accents(text)
        text = tprep.replace_currency_symbols(text)
        
        # --- spaCy ile tokenization + lemmatization + stopword removal ---
        doc = nlp(text)
        temiz = [
            t.lemma_.lower() for t in doc
            if t.is_alpha and not t.is_stop and t.pos_ in ["NOUN", "VERB", "ADJ"]
        ]
        item["clean_text"] = " ".join(temiz)
    
    print("Metin temizleme tamamlandı.")
    return veri

# TF-IDF + ANOMALİ TESPİTİ
def anomaly_tespiti(veri, contamination=0.05):
    texts = [item["clean_text"] for item in veri]
    vectorizer = TfidfVectorizer(max_features=2000)
    X = vectorizer.fit_transform(texts)

    iso = IsolationForest(contamination=contamination, random_state=42)
    labels = iso.fit_predict(X.toarray())

    for item, label in zip(veri, labels):
        item["is_anomaly"] = (label == -1)
    print("Anomali tespiti tamamlandı.")
    return veri

# SONUCU KAYDET
def temiz_json_kaydet(veri, cikti_klasoru):
    cikti_yolu = os.path.join(cikti_klasoru, "all_clean_data.json")
    with open(cikti_yolu, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
    print(f"✅ Temiz veri kaydedildi: {cikti_yolu}")

# ANA AKIŞ
if __name__ == "__main__":
    print("=== CLEAN DATA PIPELINE BAŞLIYOR ===")
    data = jsonl_dosyalarini_yukle(GIRIS_KLASORU)
    data = metin_temizle(data)
    data = anomaly_tespiti(data, contamination=0.05)
    temiz_json_kaydet(data, CIKTI_KLASORU)
    print("🎯 Tüm işlem tamamlandı! 'clean_data' klasörüne bakabilirsin.")
