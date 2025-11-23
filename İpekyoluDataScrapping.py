import instaloader
import re
import pandas as pd
from datetime import datetime

# --- AYARLAR ---
HEDEF_HESAP = "ipekyolugenclik" # Buraya kurumun kullanıcı adını yaz
CEKILECEK_POST_SAYISI = 1340 # Deneme için 50-100 ile başla, sonra artır.

# --- TEMİZLİK FONKSİYONU ---
def metni_temizle(metin):
    if not metin:
        return ""
    
    # 1. Satır sonlarını boşlukla değiştir (tek satır olsun)
    metin = metin.replace('\n', ' ')
    
    # 2. Hashtag'leri sil (Örn: #teknofest #elazığ)
    metin = re.sub(r'#\w+', '', metin)
    
    # 3. Kullanıcı etiketlerini sil (Örn: @btk_akademi) - İstersen bunu silmeyebilirsin
    metin = re.sub(r'@\w+', '', metin)
    
    # 4. Linkleri sil (http/https)
    metin = re.sub(r'http\S+', '', metin)
    
    # 5. "Link bio'da" vb. kalıpları sil (İsteğe bağlı genişletilebilir)
    metin = re.sub(r'(?i)link bio\'?da', '', metin)
    metin = re.sub(r'(?i)detaylı bilgi için', '', metin)
    
    # 6. Emojileri temizle (Basit yöntem: ASCII dışı karakterleri at)
    # Not: Emojileri tamamen atmak istemezsen bu satırı yorum satırı yap.
    # RAG için emojiler genellikle gürültüdür.
    metin = metin.encode('ascii', 'ignore').decode('ascii')
    
    # 7. Fazla boşlukları düzelt
    metin = re.sub(r'\s+', ' ', metin).strip()
    
    return metin

# --- SCRAPING İŞLEMİ ---
def instagram_veri_cek():
    L = instaloader.Instaloader()
    
    # Not: Çok fazla veri çekeceksen Instagram giriş yapmanı isteyebilir.
    # L.login("senin_kullanici_adin", "sifren") # Gerekirse açarsın
    
    try:
        profile = instaloader.Profile.from_username(L.context, HEDEF_HESAP)
    except Exception as e:
        print(f"Profil bulunamadı: {e}")
        return

    veriler = []
    print(f"--- {HEDEF_HESAP} hesabından veriler çekiliyor... ---")

    sayac = 0
    for post in profile.get_posts():
        if sayac >= CEKILECEK_POST_SAYISI:
            break
            
        ham_metin = post.caption
        if ham_metin: # Sadece açıklaması olanları al
            
            # Temizlenmiş metin
            temiz_metin = metni_temizle(ham_metin)
            
            # Tarih formatı (Örn: 2025-10-05)
            tarih = post.date.strftime("%Y-%m-%d")
            
            # Eğer temizlik sonrası metin çok kısaldıysa (sadece hashtagmiş demek ki) alma
            if len(temiz_metin) > 15: 
                # Veriyi RAG formatına uygun hale getirmek için birleştiriyoruz
                kayit = {
                    "tarih": tarih,
                    "icerik": f"[Tarih: {tarih}] {temiz_metin}",
                    "orijinal_url": f"https://www.instagram.com/p/{post.shortcode}/"
                }
                veriler.append(kayit)
                print(f"✅ Post çekildi: {tarih}")
        
        sayac += 1

    # --- KAYDETME ---
    df = pd.DataFrame(veriler)
    df.to_json(f"{HEDEF_HESAP}_temiz_veri.json", orient="records", force_ascii=False, indent=4)
    df.to_csv(f"{HEDEF_HESAP}_temiz_veri.csv", index=False) # Excel için
    
    print(f"\n🎉 İşlem Tamam! Toplam {len(veriler)} temiz veri kaydedildi.")

if __name__ == "__main__":
    instagram_veri_cek()