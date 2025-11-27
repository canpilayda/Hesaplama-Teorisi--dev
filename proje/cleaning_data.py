import os
import json
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import IsolationForest


# -------------------------
#  AYARLAR
# -------------------------

GIRIS_KLASORU = "json_cikti"
CIKTI_KLASORU = "clean_data"
os.makedirs(GIRIS_KLASORU, exist_ok=True)
os.makedirs(CIKTI_KLASORU, exist_ok=True)


# -------------------------
#  JSONL YÜKLEME
# -------------------------

def jsonl_dosyalarini_yukle(klasor):
    """Belirtilen klasördeki tüm .jsonl dosyalarını okuyup tek listeye döndürür."""
    tum_veri = []
    dosya_listesi = [d for d in os.listdir(klasor) if d.endswith(".jsonl")]

    for dosya in dosya_listesi:
        yol = os.path.join(klasor, dosya)
        with open(yol, "r", encoding="utf-8") as f:
            for satir in f:
                try:
                    item = json.loads(satir)
                    tum_veri.append(item)
                except json.JSONDecodeError:
                    print(f"⚠️ Uyarı: '{dosya}' içinde bozuk bir satır atlandı.")

    print(f"Toplam {len(tum_veri)} metin yüklendi ({len(dosya_listesi)} dosyadan).")
    return tum_veri


# -------------------------
#  METİN TEMİZLEME (spaCy)
# -------------------------

def metin_temizle_spacy(veri):
    """Türkçe spaCy modeliyle metinleri köklerine indirger, gereksiz kelimeleri kaldırır."""
    print("spaCy modeli yükleniyor (en_core_web_lg)...")
    nlp = spacy.load("en_core_web_lg")

    for item in veri:
        doc = nlp(item["text"])
        temiz = [
            t.lemma_.lower() for t in doc
            if t.is_alpha and not t.is_stop and t.pos_ in ["NOUN", "VERB", "ADJ"]
        ]
        item["clean_text"] = " ".join(temiz)

    print("Metin temizleme tamamlandı.")
    return veri


# -------------------------
#  ANOMALİ TESPİTİ (TF-IDF + IF)
# -------------------------

def anomaly_tespiti(veri, contamination=0.05):
    """TF-IDF + IsolationForest ile anormal (farklı) sayfa metinlerini tespit eder."""
    print("TF-IDF vektörleri oluşturuluyor...")
    texts = [item["clean_text"] for item in veri]
    vectorizer = TfidfVectorizer(max_features=2000)
    X = vectorizer.fit_transform(texts)

    print("Isolation Forest modeli eğitiliyor...")
    iso = IsolationForest(contamination=contamination, random_state=42)
    labels = iso.fit_predict(X.toarray())

    for item, label in zip(veri, labels):
        item["is_anomaly"] = (label == -1)

    print("Anomali tespiti tamamlandı.")
    return veri


# -------------------------
#  SONUCU KAYDETME
# -------------------------

def temiz_json_kaydet(veri, cikti_klasoru):
    """Tüm temizlenmiş veriyi tek bir JSON dosyasına kaydeder."""
    cikti_yolu = os.path.join(cikti_klasoru, "all_clean_data.json")
    with open(cikti_yolu, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)

    print(f"✅ Temiz veri kaydedildi: {cikti_yolu}")


# -------------------------
#  ANA PIPELINE FONKSİYONU
# -------------------------

def pipeline(
    giris_klasoru=GIRIS_KLASORU,
    cikti_klasoru=CIKTI_KLASORU,
    contamination=0.05
):
    print("=== CLEAN DATA PIPELINE BAŞLIYOR ===")

    data = jsonl_dosyalarini_yukle(giris_klasoru)
    data = metin_temizle_spacy(data)
    data = anomaly_tespiti(data, contamination=contamination)
    temiz_json_kaydet(data, cikti_klasoru)

    print("🎯 Tüm işlem tamamlandı! 'clean_data' klasörüne bakabilirsin.")


# -------------------------
#  __main__
# -------------------------

if __name__ == "__main__":
    pipeline()
