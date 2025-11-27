import os
import json
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import IsolationForest

# --- AYARLAR ---
# app.py'deki klasörlerle aynı olsun
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
GIRIS_KLASORU = os.path.join(BASE_DIR, "downloads")
CIKTI_KLASORU = os.path.join(BASE_DIR, "cleandata_downloads")

os.makedirs(GIRIS_KLASORU, exist_ok=True)
os.makedirs(CIKTI_KLASORU, exist_ok=True)

# Global model değişkeni (Her seferinde yükleyip vakit kaybetmeyelim)
NLP_MODEL = None


def model_yukle():
    global NLP_MODEL
    if NLP_MODEL is None:
        print("⏳ spaCy modeli yükleniyor (en_core_web_lg)...")
        try:
            NLP_MODEL = spacy.load("en_core_web_lg")
        except:
            print(
                "❌ Model bulunamadı! 'python -m spacy download en_core_web_lg' çalıştır."
            )
            return False
    return True


def verileri_yukle(klasor):
    """Downloads klasöründeki .json dosyalarını okur."""
    tum_veri = []
    # Hem .json hem .jsonl destekleyelim
    dosya_listesi = [
        d for d in os.listdir(klasor) if d.endswith(".json") or d.endswith(".jsonl")
    ]

    for dosya in dosya_listesi:
        yol = os.path.join(klasor, dosya)
        with open(yol, "r", encoding="utf-8") as f:
            try:
                # Önce standart JSON (liste) olarak dene
                icerik = json.load(f)
                if isinstance(icerik, list):
                    tum_veri.extend(icerik)
                else:
                    tum_veri.append(icerik)
            except json.JSONDecodeError:
                # JSON listesi değilse, JSONL (satır satır) olarak dene
                f.seek(0)
                for satir in f:
                    try:
                        tum_veri.append(json.loads(satir))
                    except:
                        pass

    print(f"✅ Toplam {len(tum_veri)} satır veri yüklendi.")
    return tum_veri


def metin_temizle_spacy(veri):
    if not model_yukle():
        return veri

    print("🧹 Metin temizliği başladı...")
    # İşlem uzun sürerse diye kullanıcıya en azından log basıyoruz
    for item in veri:
        # 'text' alanı yoksa atla
        if "text" not in item:
            continue

        doc = NLP_MODEL(item["text"])
        temiz = [
            t.lemma_.lower()
            for t in doc
            if t.is_alpha and not t.is_stop and t.pos_ in ["NOUN", "VERB", "ADJ"]
        ]
        item["clean_text"] = " ".join(temiz)

    return veri


def anomaly_tespiti(veri, contamination=0.05):
    print("🕵️ Anomali tespiti yapılıyor...")
    # Sadece temizlenmiş metni olanları al
    gecerli_veri = [d for d in veri if "clean_text" in d and d["clean_text"].strip()]

    if not gecerli_veri:
        print("⚠️ Yeterli veri yok, anomali tespiti atlandı.")
        return veri

    texts = [item["clean_text"] for item in gecerli_veri]

    # Vektörleştirme
    vectorizer = TfidfVectorizer(max_features=2000)
    try:
        X = vectorizer.fit_transform(texts)

        # Isolation Forest
        iso = IsolationForest(contamination=contamination, random_state=42)
        labels = iso.fit_predict(X.toarray())

        # Sonuçları orijinal veriye işle
        # Dikkat: gecerli_veri sırasıyla texts sırası aynıdır.
        for i, item in enumerate(gecerli_veri):
            item["is_anomaly"] = True if labels[i] == -1 else False
            item["anomaly_score"] = "Anormal" if labels[i] == -1 else "Normal"

    except ValueError:
        print("⚠️ Vektörleştirme hatası (veri çok az olabilir).")

    return veri


def pipeline_calistir():
    """Tüm süreci yöneten ana fonksiyon (App.py buradan çağıracak)"""
    data = verileri_yukle(GIRIS_KLASORU)

    if not data:
        return {"durum": "hata", "mesaj": "İşlenecek veri bulunamadı."}

    data = metin_temizle_spacy(data)
    data = anomaly_tespiti(data)

    # Sonucu Kaydet
    cikti_dosyasi = "all_clean_data.json"
    cikti_yolu = os.path.join(CIKTI_KLASORU, cikti_dosyasi)

    with open(cikti_yolu, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {
        "durum": "basarili",
        "mesaj": f"Temizlik bitti. {len(data)} satır işlendi.",
        "dosya_yolu": cikti_dosyasi,
        "veri": data[:5],  # Önizleme için ilk 5 kaydı dönelim
    }


if __name__ == "__main__":
    pipeline_calistir()
