import os
import json
import spacy
from textacy.preprocessing import normalize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import IsolationForest

# AYARLAR
GIRIS_KLASORU = "json_cikti"
CIKTI_KLASORU = "clean_data"
os.makedirs(GIRIS_KLASORU, exist_ok=True)
os.makedirs(CIKTI_KLASORU, exist_ok=True)

# JSONL YÜKLE
def jsonl_dosyalarini_yukle(klasor):
    tum_veri = []
    for dosya in os.listdir(klasor):
        if dosya.endswith(".jsonl"):
            with open(os.path.join(klasor, dosya), "r", encoding="utf-8") as f:
                for satir in f:
                    try:
                        tum_veri.append(json.loads(satir))
                    except json.JSONDecodeError:
                        pass
    return tum_veri
# --- TİRELERİ BOŞLUĞA ÇEVİRME FONKSİYONU ---
def hyphen_to_space(text):
    return text.replace("-", " ")

# METİN TEMİZLE
def metin_temizle(veri, nlp_model):
    for item in veri:
        text = item.get("text", "")

        # --- TEXTACY NORMALIZE --- (regex yok)
        text = normalize.whitespace(text)
        text = normalize.unicode(text)
        text = normalize.quotation_marks(text)
        text = hyphen_to_space(text)

        # --- spaCy lemma ve stopword temizleme ---
        doc = nlp_model(text)
        temiz = [
            t.lemma_.lower() for t in doc
            if t.is_alpha and not t.is_stop
        ]
        item["clean_text"] = " ".join(temiz)

    return veri

# ANOMALİ TESPİTİ
def anomaly_tespiti(veri, contamination=0.05):
    texts = [item["clean_text"] for item in veri]
    vectorizer = TfidfVectorizer(max_features=2000)
    X = vectorizer.fit_transform(texts)

    iso = IsolationForest(contamination=contamination, random_state=42)
    labels = iso.fit_predict(X.toarray())

    for item, label in zip(veri, labels):
        item["is_anomaly"] = (label == -1)

    return veri

# JSON KAYDET
def temiz_json_kaydet(veri, cikti_klasoru):
    with open(os.path.join(cikti_klasoru, "all_clean_data.json"), "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)

# ANA AKIŞ
if __name__ == "__main__":
    nlp = spacy.load("en_core_web_lg")  # İngilizce makale için
    data = jsonl_dosyalarini_yukle(GIRIS_KLASORU)
    data = metin_temizle(data, nlp)
    data = anomaly_tespiti(data)
    temiz_json_kaydet(data, CIKTI_KLASORU)