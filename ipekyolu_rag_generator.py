import json
import os
import time
import google.generativeai as genai
from tqdm import tqdm
from datetime import datetime

# ================= AYARLAR =================
# 1. API ANAHTARINI BURAYA YAPIŞTIR
API_KEY = "AIzaSyCFjVAq-g4Q8iV3G7BZNbGfvtJsk1hnTeE"

# 2. Dosya Yolları (Senin yüklediğin dosya)
GIRIS_DOSYASI = 'haberler.json'
ANA_KLASOR = "IPEKYOLU_RAG_VERISETI"

# 3. Model (Hızlı ve Ücretsiz)
MODEL_NAME = 'models/gemini-2.0-flash'

# ================= GEMINI AYARLARI =================
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL_NAME)

# ================= HEDEF DOSYA HARİTASI =================
DOSYA_HARITASI = """
1. "01_TEMEL_BILGILER/1.3_merkez_ozellikleri.json": Genel merkez tanıtımı, tarihçe, açılış, protokol ziyaretleri.
2. "03_PROJELER_VE_BASARILAR/3.2_roket_ve_yarismalar.json": TEKNOFEST, yarışma dereceleri, ödüller, Ar-Ge ürünleri (SkyLogic vb.).
3. "04_ETKINLIK_VE_SSS/4.1_kariyer_ve_etkinlik_turleri.json": Festivaller, kamplar, sosyal etkinlikler.
4. "02_PROGRAMLAR_ATOLYELER_EGITIMLER/2.4_gonulluluk_bilgisi.json": Gönüllülük, uluslararası projeler, Erasmus.
5. "05_EK_DOKUMANLAR_VE_FINANS/5.3_program_takvimi_ve_sureler.json": Tarihli duyurular.
"""

# ================= SİSTEM PROMPTU =================
SYSTEM_PROMPT = f"""
Sen "İpek Yolu Uluslararası Çocuk ve Gençlik Çalışmaları Merkezi" için veri işleyen uzman bir asistansın.
Sana bir Haber Metni verilecek.

🔴 KURALLAR:
1. Kurum adını her zaman **"İpek Yolu"** (ayrı) yaz.
2. Cevaplar metne sadık kalmalı.
3. Tarih bilgisi varsa mutlaka kullan (Örn: "2021 yılında...").
4. "related_questions" alanına mutlaka 2-3 adet ilgili soru ekle.

GÖREVLERİN:
1. Metni analiz et ve aşağıdaki dosya yollarından hangisine EN UYGUN olduğuna karar ver:
{DOSYA_HARITASI}

2. Metne dayalı 1 adet Soru-Cevap oluştur.

YANIT FORMATI (Sadece JSON):
{{
  "hedef_dosya": "SECILEN_DOSYA_YOLU",
  "qa_data": {{
      "question": "...",
      "answer": "...",
      "category": "...",
      "keywords": ["anahtar1", "anahtar2"],
      "priority": "high",
      "related_questions": [
          "İlgili soru 1?",
          "İlgili soru 2?"
      ]
  }}
}}
"""

# Standart Notlar
STANDART_NOTES = {
    "chunking_strategy": "Her Q&A çifti bağımsız ve anlaşılır olacak şekilde yapılandırıldı.",
    "augmentation_notes": "Haber kaynaklı veriler kullanılarak zenginleştirildi. Tarih ve resmi detaylar eklendi.",
    "answer_length": "Cevaplar 50-500 kelime aralığına uygun tutuldu.",
    "context_inclusion": "Her cevap kendi başına anlamlıdır."
}

def ai_analiz_et(metin, tarih):
    prompt = f"{SYSTEM_PROMPT}\n\nANALİZ EDİLECEK VERİ:\nTARİH: {tarih}\nMETİN: {metin}"
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except:
        return None

def main():
    # Klasörleri oluştur (Garanti olsun)
    for path_str in DOSYA_HARITASI.split('\n'):
        if '"' in path_str:
            rel_path = path_str.split('"')[1]
            klasor = os.path.dirname(os.path.join(ANA_KLASOR, rel_path))
            os.makedirs(klasor, exist_ok=True)

    # Veriyi Oku (Senin oluşturduğun dosya)
    try:
        with open(GIRIS_DOSYASI, 'r', encoding='utf-8') as f:
            posts = json.load(f)
    except:
        print(f"HATA: '{GIRIS_DOSYASI}' dosyası bulunamadı! Dosya ismini kontrol et.")
        return

    print(f"🚀 {len(posts)} haber işleniyor... (Haber Kaynaklı Veri)")
    
    basarili_sayac = 0

    for i, post in tqdm(enumerate(posts), total=len(posts)): 
        icerik = post.get('icerik', '')
        tarih = post.get('tarih', '')

        if len(icerik) < 20: continue

        sonuc = ai_analiz_et(icerik, tarih)

        if sonuc:
            hedef_dosya = sonuc.get("hedef_dosya")
            qa_veri = sonuc.get("qa_data")
            
            if hedef_dosya and qa_veri:
                # Kaynak ID
                qa_veri['source_ids'] = [f"news_{tarih}_{i}"]

                tam_yol = os.path.join(ANA_KLASOR, hedef_dosya)
                
                # Dosya Yönetimi
                mevcut_veri = {
                    "metadata": {
                        "file_name": os.path.basename(hedef_dosya),
                        "category": os.path.dirname(hedef_dosya),
                        "sub_category": "Haber Kaynaklı Veri",
                        "last_updated": datetime.now().strftime("%Y-%m-%d"),
                        "version": "1.0"
                    },
                    "data": [],
                    "notes": STANDART_NOTES
                }
                
                if os.path.exists(tam_yol):
                    try:
                        with open(tam_yol, 'r', encoding='utf-8') as f:
                            okunan = json.load(f)
                            if "data" in okunan:
                                mevcut_veri = okunan
                    except: pass

                mevcut_veri["data"].append(qa_veri)
                
                with open(tam_yol, 'w', encoding='utf-8') as f:
                    json.dump(mevcut_veri, f, ensure_ascii=False, indent=4)
                
                basarili_sayac += 1
        
        # Hız Sınırı Koruması
        time.sleep(4)

    print(f"\n✅ İŞLEM TAMAMLANDI! Toplam {basarili_sayac} haber verisi sisteme eklendi.")

if __name__ == "__main__":
    main()