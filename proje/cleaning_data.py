import os
import json
import spacy
import time
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import IsolationForest

# ==========================
# AYARLAR (SETTINGS)
# ==========================
GIRIS_KLASORU = "denemecikti"
CIKTI_KLASORU = "denemedata"
os.makedirs(CIKTI_KLASORU, exist_ok=True)

NUM_CORES = 4 # Güvenli çekirdek sayısı (sadece IsolationForest için)

# 🚨 RAM KRİTİK AYARLAR
SPACY_MODEL = "en_core_web_lg" 
MAX_FEATURES_COUNT = 1000      

# ==========================
# 1. TÜM JSONL DOSYALARINI OKU
# ==========================
def load_jsonl_files(folder):
    """Belirtilen klasördeki tüm .jsonl dosyalarını okuyup tek listeye döndürür."""
    start_time = time.time()
    tum_veri = []
    
    for file_name in os.listdir(folder):
        if file_name.endswith(".jsonl"):
            path = os.path.join(folder, file_name)
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        item = json.loads(line)
                        tum_veri.append(item)
                    except json.JSONDecodeError:
                        print(f"⚠️ Uyarı: '{file_name}' içinde bozuk bir satır atlandı.")
    end_time = time.time()
    gecen_sure = end_time - start_time
    print(f"Toplam {len(tum_veri)} metin yüklendi ({len([f for f in os.listdir(folder) if f.endswith('.jsonl')])} dosyadan).")
    print(f"   [Süre: {gecen_sure:.2f} saniye]")
    return tum_veri


# ==========================
# 2. METİN TEMİZLİĞİ (spaCy) LG MODEL
# ==========================
def clean_text_spacy(data):
    """Lemmatizes and removes stopwords/punctuation using the LG spaCy model (Sequential Processing)."""
    print(f"Loading spaCy model ({SPACY_MODEL})...") 
    nlp = spacy.load(SPACY_MODEL, disable=["parser", "ner"]) 
    
    start_time = time.time()
    texts = [item["text"] for item in data]
    print(f"   🐢 Sıralı işlem başlatıldı (Single-Core). Bu adım en uzun sürecek.")
    
    # nlp.pipe ile metinleri sıralı işle
    processed_docs = nlp.pipe(texts, batch_size=2000) 
    
    for item, doc in zip(data, processed_docs):
        cleaned = [
            t.lemma_.lower() for t in doc
            if t.is_alpha and not t.is_stop and t.pos_ in ["NOUN", "VERB", "ADJ"]
        ]
        item["clean_text"] = " ".join(cleaned)
        
    end_time = time.time()
    gecen_sure = end_time - start_time
    print("Text cleaning completed.")
    print(f"   [Süre: {gecen_sure:.2f} saniye]")
    return data


# ==========================
# 3. TF-IDF + ANOMALİ TESPİTİ - MATRİS KÜÇÜLTÜLDÜ
# ==========================
def detect_anomaly(data, contamination=0.01, n_jobs=NUM_CORES):
    """Detects anomalous (different) page texts using TF-IDF + IsolationForest."""
    start_time = time.time()
    
    print(f"Creating TF-IDF vectors (Max Features: {MAX_FEATURES_COUNT})...")
    texts = [item["clean_text"] for item in data]
    vectorizer = TfidfVectorizer(max_features=MAX_FEATURES_COUNT) 
    X = vectorizer.fit_transform(texts)

    print("Training Isolation Forest model...")
    iso = IsolationForest(contamination=contamination, random_state=42, n_jobs=n_jobs) 
    labels = iso.fit_predict(X.toarray())

    for item, label in zip(data, labels):
        # 🚨 HATA GİDERİLDİ: bool'u str'ye çevirdik
        item["is_anomaly"] = str(label == -1) 
        
    end_time = time.time()
    gecen_sure = end_time - start_time

    print("Anomaly detection completed.")
    print(f"   [Süre: {gecen_sure:.2f} saniye]")
    return data


# ==========================
# 4. SONUCU KAYDET
# ==========================
def save_cleaned_json(data, output_folder):
    """Tüm temizlenmiş veriyi tek bir JSON dosyasına kaydeder."""
    start_time = time.time()
    output_path = os.path.join(output_folder, "all_clean_data.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    end_time = time.time()
    gecen_sure = end_time - start_time

    print(f"✅ Temiz veri kaydedildi: {output_path}")
    print(f"   [Süre: {gecen_sure:.2f} saniye]")


# ==========================
# ANA AKIŞ (MAIN FLOW)
# ==========================
if __name__ == "__main__":
    
    genel_start_time = time.time()
    
    print("=== CLEAN DATA PIPELINE BAŞLIYOR (LG Model + Düşük Matris Modu) ===")

    data = load_jsonl_files(GIRIS_KLASORU)
    data = clean_text_spacy(data)
    data = detect_anomaly(data)
    
    # Anomali Raporu
    anomali_sayisi = sum(1 for item in data if item["is_anomaly"])
    toplam_veri = len(data)
    anomali_yuzdesi = (anomali_sayisi / toplam_veri) * 100 if toplam_veri > 0 else 0
    
    print("-" * 30)
    print(f"📊 VERİ KALİTE RAPORU:")
    print(f"Toplam sayfa/metin: {toplam_veri}")
    print(f"Anomali Olarak İşaretlenen: {anomali_sayisi} adet")
    print(f"Verinin Kayıp/Aykırı Yüzdesi: {anomali_yuzdesi:.2f}%")
    print("-" * 30)

    save_cleaned_json(data, CIKTI_KLASORU)
    
    genel_end_time = time.time()
    genel_sure = genel_end_time - genel_start_time
    
    print("--------------------------------")
    print(f"🎯 Tüm işlem tamamlandı! TOPLAM SÜRE: {genel_sure:.2f} saniye")
    print("--------------------------------")