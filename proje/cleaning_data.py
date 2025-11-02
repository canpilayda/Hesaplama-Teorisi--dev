import json, os, spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import IsolationForest

# 1. Dosyayı oku
with open("json_cikti/dosya.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 2. spaCy ile temizle
nlp = spacy.load("tr_core_news_lg")
for item in data:
    doc = nlp(item["text"])
    item["clean_text"] = " ".join([
        t.lemma_.lower() for t in doc
        if t.is_alpha and not t.is_stop and t.pos_ in ["NOUN", "VERB", "ADJ"]
    ])

# 3. TF-IDF vektörleştirme
texts = [item["clean_text"] for item in data]
vectorizer = TfidfVectorizer(max_features=2000)
X = vectorizer.fit_transform(texts)

# 4. Isolation Forest ile anomali tespiti
iso = IsolationForest(contamination=0.05, random_state=42)
labels = iso.fit_predict(X.toarray())

for item, label in zip(data, labels):
    item["is_anomaly"] = (label == -1)

# 5. Clean JSON’a kaydet
os.makedirs("clean_data", exist_ok=True)
with open("clean_data/dosya_clean.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
