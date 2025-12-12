import json
import os
import time
import re
import google.generativeai as genai
from tqdm import tqdm
from datetime import datetime

# ================= AYARLAR =================
GIRIS_DOSYASI = r'C:\Users\Atakan\Documents\GitHub\ipekgpt\Data Mining\ek_soru_cevap (1).txt'
CIKIS_KLASORU = r'C:\Users\Atakan\Documents\GitHub\ipekgpt\IPEKYOLU_RAG_VERISETI'

# Model Ayarları
MODEL_NAME = 'models/gemini-2.5-flash'
genai.configure(api_key="AIzaSyA8iETrS_zkxCemGZgUvBcQLPQDcILBBWs")
model = genai.GenerativeModel(MODEL_NAME)

# ================= HEDEF DOSYA HARİTASI =================
DOSYA_HARITASI = """
Metne göre en uygun dosyayı seç:
1. "01_TEMEL_BILGILER/genel_bilgiler.json" → Merkez tanıtımı, çalışma saatleri, ulaşım, kurucu bilgisi
2. "02_PROGRAMLAR_ATOLYELER_EGITIMLER/egitim_bilgileri.json" → Eğitimler, yaş grupları, drone, 3D yazıcı
3. "02_PROGRAMLAR_ATOLYELER_EGITIMLER/gonulluluk.json" → Gönüllülük, staj, başvuru şartları
4. "03_PROJELER_VE_BASARILAR/teknofest.json" → TEKNOFEST, yarışmalar, ödüller, roket
5. "04_ETKINLIK_VE_SSS/sohbet_kurallari.json" → Selamlaşma, kişisel sorular, vedalaşma
"""

# ================= SİSTEM PROMPTU =================
SYSTEM_PROMPT = f"""
Sen "İpek Yolu Uluslararası Çocuk ve Gençlik Çalışmaları Merkezi" için RAG veri seti oluşturan bir asistansın.
Sana verilen metni analiz edip yapılandırılmış soru-cevap verisi üreteceksin.

KURALLAR:
- Kurum adı: "İpek Yolu" (iki kelime ayrı)
- Cevap sadece metindeki bilgiye dayansın
- Eğer metinde "=>" varsa, sol taraf soru, sağ taraf cevap

DOSYA SEÇİMİ:
{DOSYA_HARITASI}

JSON FORMATI (sadece bu formatı döndür):
{{
  "hedef_dosya": "DOSYA_YOLU",
  "qa_data": {{
      "question": "Soru?",
      "answer": "Cevap.",
      "category": "Kategori",
      "keywords": ["kelime1", "kelime2", "kelime3"],
      "priority": "high veya medium veya low",
      "related_questions": ["İlgili soru 1?", "İlgili soru 2?", "İlgili soru 3?"]
  }}
}}
"""

# Standart Notlar
STANDART_NOTES = {
    "chunking_strategy": "Her Q&A çifti bağımsız ve anlaşılır olacak şekilde yapılandırıldı.",
    "augmentation_notes": "TXT verileri kullanılarak zenginleştirildi. Tarih, yer ve içerik detayları eklendi.",
    "answer_length": "Cevaplar 50-500 kelime aralığına uygun tutuldu.",
    "context_inclusion": "Her cevap kendi başına anlamlıdır."
}

def ai_analiz_et(metin):
    """Gemini API ile metni analiz et ve soru-cevap üret"""
    prompt = f"{SYSTEM_PROMPT}\n\nMETİN:\n{metin}"
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"  ⚠️ API Hatası: {e}")
        return None

def metinleri_ayir(dosya_yolu):
    """TXT dosyasını anlamlı parçalara ayır"""
    with open(dosya_yolu, 'r', encoding='utf-8') as f:
        icerik = f.read()
    
    # Çift veya daha fazla boş satırla ayır
    parcalar = re.split(r'\n\s*\n+', icerik)
    
    # Boş ve çok kısa olanları filtrele
    metinler = []
    for p in parcalar:
        temiz = p.strip()
        if temiz and len(temiz) > 15:
            metinler.append(temiz)
    
    return metinler

def dosyaya_kaydet(hedef_dosya, qa_veri, index):
    """Soru-cevabı hedef JSON dosyasına ekle"""
    tam_yol = os.path.join(CIKIS_KLASORU, hedef_dosya)
    
    # Klasörü oluştur
    os.makedirs(os.path.dirname(tam_yol), exist_ok=True)
    
    # Kaynak ID ekle
    qa_veri['source_ids'] = [f"txt_import_{index}"]
    
    # Mevcut veriyi oku veya yeni oluştur
    if os.path.exists(tam_yol):
        try:
            with open(tam_yol, 'r', encoding='utf-8') as f:
                mevcut = json.load(f)
        except:
            mevcut = {"metadata": {}, "data": [], "notes": STANDART_NOTES}
    else:
        mevcut = {
            "metadata": {
                "file_name": os.path.basename(hedef_dosya),
                "category": os.path.dirname(hedef_dosya),
                "sub_category": "TXT Kaynaklı Veri",
                "last_updated": datetime.now().strftime("%Y-%m-%d"),
                "version": "1.0"
            },
            "data": [],
            "notes": STANDART_NOTES
        }
    
    # Yeni veriyi ekle
    mevcut["data"].append(qa_veri)
    mevcut["metadata"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    
    # Kaydet
    with open(tam_yol, 'w', encoding='utf-8') as f:
        json.dump(mevcut, f, ensure_ascii=False, indent=4)
    
    return tam_yol

def main():
    print("=" * 60)
    print("İPEK YOLU RAG VERİ SETİ OLUŞTURUCU")
    print("=" * 60)
    
    # Metinleri oku
    try:
        metinler = metinleri_ayir(GIRIS_DOSYASI)
        print(f"\n📄 {len(metinler)} adet metin parçası bulundu.\n")
    except Exception as e:
        print(f"❌ Dosya okunamadı: {e}")
        return
    
    basarili = 0
    hatali = 0
    
    for i, metin in enumerate(tqdm(metinler, desc="İşleniyor")):
        # Kısa bilgi göster
        kisaltilmis = metin[:50].replace('\n', ' ') + "..." if len(metin) > 50 else metin
        print(f"\n[{i+1}/{len(metinler)}] {kisaltilmis}")
        
        # AI ile analiz et
        sonuc = ai_analiz_et(metin)
        
        if sonuc and sonuc.get("hedef_dosya") and sonuc.get("qa_data"):
            hedef = sonuc["hedef_dosya"]
            qa = sonuc["qa_data"]
            
            # Kaydet
            dosya_yolu = dosyaya_kaydet(hedef, qa, i)
            print(f"  ✅ Kaydedildi: {hedef}")
            print(f"     Soru: {qa.get('question', '')[:60]}...")
            basarili += 1
        else:
            print(f"  ❌ İşlenemedi")
            hatali += 1
        
        # API rate limit - 20 saniye bekle
        time.sleep(20)
    
    print("\n" + "=" * 60)
    print(f"✅ TAMAMLANDI!")
    print(f"   Başarılı: {basarili}")
    print(f"   Hatalı: {hatali}")
    print(f"   Çıktı klasörü: {CIKIS_KLASORU}")
    print("=" * 60)

if __name__ == "__main__":
    main()
