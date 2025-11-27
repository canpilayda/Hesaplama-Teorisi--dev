from flask import (
    Flask,
    render_template,
    request,
    send_file,
    send_from_directory,
    redirect,
    url_for,
    jsonify,
)
import os
import threading  # Arka plan işlemleri için
import uuid  # Benzersiz işlem kimliği için
from werkzeug.utils import secure_filename
import json  # Sonuçları okumak için
import pdf_processor  # Senin sadık modülün

# --- DÜZELTME BURADA ---
# Dosya adın data_cleaning.py olduğu için import böyle olmalı:
import data_cleaning

# -----------------------

app = Flask(__name__)

# --- KLASÖR YAPILANDIRMASI ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, "downloads")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["DOWNLOAD_FOLDER"] = DOWNLOAD_FOLDER

# --- GLOBAL HAFIZA (İlerleme Durumu İçin) ---
# Format: {'islem_id_123': 55} -> %55 tamamlandı demek
ISLEM_DURUMU = {}


def dosya_listesini_getir():
    """Uploads klasöründeki PDF'leri alfabetik listeler."""
    if not os.path.exists(app.config["UPLOAD_FOLDER"]):
        return []
    return sorted(
        [
            f
            for f in os.listdir(app.config["UPLOAD_FOLDER"])
            if f.lower().endswith(".pdf")
        ]
    )


# --- ARKA PLAN İŞÇİSİ (THREAD) ---
def arka_planda_isle(dosya_yolu, islem_id, dosya_adi):
    """
    Bu fonksiyon ana programdan bağımsız bir thread içinde çalışır.
    """
    try:
        base_name = os.path.splitext(dosya_adi)[0]

        # İlerleme durumunu güncelleyen callback fonksiyonu
        def ilerleme_guncelle(yuzde):
            ISLEM_DURUMU[islem_id] = yuzde

        # 1. Analiz Başlat (Callback ile)
        analiz_verisi = pdf_processor.pdf_isleyici_tam(dosya_yolu)

        # Manuel olarak %50 yapalım
        ISLEM_DURUMU[islem_id] = 50

        # 2. Dosyaları Kaydet
        json_path = os.path.join(app.config["DOWNLOAD_FOLDER"], base_name + ".json")
        word_path = os.path.join(app.config["DOWNLOAD_FOLDER"], base_name + ".docx")

        # JSON Kaydet
        pdf_processor.json_olarak_kaydet(analiz_verisi, json_path)

        # WORD Kaydet
        pdf_processor.word_olarak_kaydet(analiz_verisi, word_path)

        # İşlem Bitti
        ISLEM_DURUMU[islem_id] = 100

    except Exception as e:
        print(f"Arka plan hatası: {e}")
        ISLEM_DURUMU[islem_id] = 100  # Hata olsa da bitir


@app.route("/ai-temizle")
def ai_temizle():
    """
    Tüm downloads klasörünü alır, temizler, anomali tespiti yapar.
    """
    try:
        # data_cleaning modülündeki fonksiyonu çağır
        sonuc = data_cleaning.pipeline_calistir()

        if sonuc["durum"] == "hata":
            return jsonify({"error": sonuc["mesaj"]}), 400

        return jsonify(sonuc)

    except Exception as e:
        print(f"AI Pipeline Hatası: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/ai-indir/<dosya_adi>")
def ai_indir(dosya_adi):
    """Temizlenmiş veriyi indirmek için"""
    klasor = data_cleaning.CIKTI_KLASORU
    return send_file(os.path.join(klasor, dosya_adi), as_attachment=True)


# --- ROUTE: ANA SAYFA & YÜKLEME ---
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if "pdf_files" not in request.files:
            return redirect(request.url)

        files = request.files.getlist("pdf_files")

        for file in files:
            if file.filename == "":
                continue
            if file:
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(file_path)

                # --- CACHE TEMİZLİĞİ ---
                base_name = os.path.splitext(filename)[0]
                json_path = os.path.join(
                    app.config["DOWNLOAD_FOLDER"], base_name + ".json"
                )
                word_path = os.path.join(
                    app.config["DOWNLOAD_FOLDER"], base_name + ".docx"
                )

                if os.path.exists(json_path):
                    os.remove(json_path)
                if os.path.exists(word_path):
                    os.remove(word_path)
                # -----------------------

        return redirect(url_for("index"))

    return render_template(
        "index.html", dosyalar=dosya_listesini_getir(), veri_var=False
    )


# --- API: İŞLEM BAŞLATMA (CACHE KONTROLLÜ) ---
@app.route("/baslat/<dosya_adi>")
def islemi_baslat(dosya_adi):
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], dosya_adi)
    if not os.path.exists(file_path):
        return jsonify({"error": "Dosya bulunamadı"}), 404

    base_name = os.path.splitext(dosya_adi)[0]
    json_path = os.path.join(app.config["DOWNLOAD_FOLDER"], base_name + ".json")
    word_path = os.path.join(app.config["DOWNLOAD_FOLDER"], base_name + ".docx")

    # --- CACHE KONTROLÜ ---
    if os.path.exists(json_path) and os.path.exists(word_path):
        print(f"⚡ CACHE: {dosya_adi} önbellekten getiriliyor.")
        islem_id = str(uuid.uuid4())
        ISLEM_DURUMU[islem_id] = 100  # Direkt bitti de
        return jsonify({"islem_id": islem_id, "cached": True})
    # ----------------------

    # Cache yoksa yeni işlem başlat
    islem_id = str(uuid.uuid4())
    ISLEM_DURUMU[islem_id] = 0

    # Thread Başlat
    thread = threading.Thread(
        target=arka_planda_isle, args=(file_path, islem_id, dosya_adi)
    )
    thread.start()

    return jsonify({"islem_id": islem_id, "cached": False})


# --- API: DURUM SORMA ---
@app.route("/durum/<islem_id>")
def durum_sor(islem_id):
    yuzde = ISLEM_DURUMU.get(islem_id, None)
    if yuzde is None:
        return jsonify({"error": "İşlem yok"}), 404
    return jsonify({"yuzde": yuzde})


# --- ROUTE: SONUÇ SAYFASI ---
@app.route("/sonuc/<dosya_adi>")
def sonucu_goster(dosya_adi):
    base_name = os.path.splitext(dosya_adi)[0]
    json_path = os.path.join(app.config["DOWNLOAD_FOLDER"], base_name + ".json")

    ekran_metni = ""
    # Hazır JSON dosyasından okuyup ekrana basıyoruz
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            veri = json.load(f)
            for satir in veri:
                ekran_metni += f"--- Sayfa {satir['page_num']} ---\n{satir['text']}\n\n"
    else:
        ekran_metni = "Hata: Analiz sonucu bulunamadı. Lütfen tekrar deneyin."

    return render_template(
        "index.html",
        dosyalar=dosya_listesini_getir(),
        aktif_dosya=dosya_adi,
        metin=ekran_metni,
        ikinci_alan="Gelecek Özellikler (AI Analiz, Özet, Chat) burada yer alacak...",
        dosya_adi=base_name,
        veri_var=True,
    )


# --- YARDIMCI ROUTE'LAR ---
@app.route("/goster/<dosya_adi>")
def pdf_goster(dosya_adi):
    return send_from_directory(app.config["UPLOAD_FOLDER"], dosya_adi)


@app.route("/indir/<tur>/<dosya_adi>")
def indir(tur, dosya_adi):
    klasor = app.config["DOWNLOAD_FOLDER"]
    if tur == "json":
        filename = f"{dosya_adi}.json"
        mimetype = "application/json"
    elif tur == "word":
        filename = f"{dosya_adi}.docx"
        mimetype = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    else:
        return "Hata", 400

    return send_file(
        os.path.join(klasor, filename),
        as_attachment=True,
        download_name=filename,
        mimetype=mimetype,
    )


if __name__ == "__main__":
    app.run(debug=True, threaded=True)
