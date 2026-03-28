import streamlit as st
import pandas as pd
import cloudscraper
from bs4 import BeautifulSoup
import re
from datetime import datetime
from PIL import Image
from io import BytesIO
import requests

# --- 1. AYARLAR VE KONFİGÜRASYON ---
st.set_page_config(page_title="Emlak Gözcü v2.0 | İlan Karşılaştırma", layout="wide")

# --- 2. HAFIZA (Session State) ---
# Görselleri ve verileri ayrı ayrı tutuyoruz
if 'ilan_verileri' not in st.session_state:
    st.session_state.ilan_verileri = pd.DataFrame(columns=[
        "İlan No", "Tarih", "Başlık", "Fiyat (TL)", "m2 (Brüt)", "m2 Fiyatı", "Oda Sayısı", "Bina Yaşı", "Bulunduğu Kat", "Isıtma", "Link"
    ])
if 'ilan_gorselleri' not in st.session_state:
    st.session_state.ilan_gorselleri = {}

# --- 3. GELİŞMİŞ SCRAPER FONKSİYONU ---
def scrape_all_details(url):
    # Bot korumalarını aşmak için cloudscraper kullanıyoruz
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
    
    try:
        response = scraper.get(url, timeout=15)
        if response.status_code != 200: return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        text_content = soup.get_text()
        
        # --- A. Veri Çekme Mekanizması ---
        # 1. Fiyat
        prices = re.findall(r'(\d{1,3}(?:\.\d{3})+)[\s]?TL', text_content)
        fiyat = int(prices[0].replace(".", "")) if prices else 0
        
        # 2. Metrekare (Genel arama)
        m2s = re.findall(r'(\d{2,4})[\s]?m²', text_content)
        m2 = int(m2s[0]) if m2s else 0
        
        # 3. Oda Sayısı (Örn: 3+1, 2+1)
        rooms = re.findall(r'(\d\+\d)', text_content)
        oda = rooms[0] if rooms else "Bulunamadı"
        
        # 4. Bina Yaşı (Örn: 5-10 arası, 0 (Yeni))
        ages = re.findall(r'Bina Yaşı\s*:\s*([\w\s-]+)', text_content, re.IGNORECASE)
        yas = ages[0].strip() if ages else "Bulunamadı"
        
        # 5. Başlık
        title = soup.title.string.strip() if soup.title else "İlan Başlığı"
        
        # --- B. Görsel Çekme Mekanizması (Kritik Bölüm) ---
        img_url = None
        
        # Emlakjet, Sahibinden vb. için yaygın görsel sınıflarını arıyoruz
        # Not: Bu kısımlar sitelerin HTML yapısına göre güncellenmelidir.
        possible_imgs = [
            soup.find("img", {"class": re.compile(r"class|image|gallery|poster", re.IGNORECASE)}),
            soup.find("meta", {"property": "og:image"}), # Genelde en garantisidir
            soup.find("link", {"rel": "image_src"})
        ]
        
        for img in possible_imgs:
            if img:
                if img.has_attr('content'): img_url = img['content']
                elif img.has_attr('src'): img_url = img['src']
                elif img.has_attr('data-src'): img_url = img['data-src']
                if img_url: break
        
        # Eğer görsel URL'si bulduysak, onu indirip sıkıştıralım
        img_object = None
        if img_url:
            try:
                img_response = requests.get(img_url, timeout=5)
                img_object = Image.open(BytesIO(img_response.content))
                # Sıkıştırma (Örn: Max 200px genişlik)
                img_object.thumbnail((200, 200)) 
            except:
                img_object = None # Görsel indirilemezse None dön
                
        return {
            "title": title,
            "fiyat": fiyat,
            "m2": m2,
            "oda": oda,
            "yas": yas,
            "image": img_object
        }
    except Exception as e:
        print(f"Hata: {e}")
        return None

# --- 4. ARAYÜZ ---
st.title("🏗️ Emlak Gözcü v2.0 | Profesyonel Kıyaslama")
st.markdown("Seçtiğiniz ilanların linklerini yapıştırın, tüm verileri ve görselleri yan yana kıyaslayın.")

# İlan Ekleme Alanı
url_input = st.text_input("Yeni İlan Linkini Buraya Yapıştırın:")

if url_input:
    # Aynı ilan zaten var mı kontrolü
    if url_input in st.session_state.ilan_verileri['Link'].values:
        st.warning("Bu ilan zaten listenizde var.")
    else:
        with st.spinner('İlanın tüm verileri ve görseli çekiliyor...'):
            data = scrape_all_details(url_input)
            
            if data and data['fiyat'] > 0:
                # Hesaplama
                m2_fiyati = int(data['fiyat'] / data['m2']) if data['m2'] > 0 else 0
                ilan_no = f"ILAN_{len(st.session_state.ilan_verileri) + 1}"
                
                # Veriyi DataFrame'e ekleme
                yeni_ilan = {
                    "İlan No": ilan_no,
                    "Tarih": datetime.now().strftime("%d/%m/%Y"),
                    "Başlık": data['title'],
                    "Fiyat (TL)": f"{data['fiyat']:,}",
                    "m2 (Brüt)": data['m2'],
                    "m2 Fiyatı": m2_fiyati,
                    "Oda Sayısı": data['oda'],
                    "Bina Yaşı": data['yas'],
                    "Isıtma": "Veri Çekilemedi", # Scraper'a eklenmeli
                    "Link": url_input
                }
                
                st.session_state.ilan_verileri = pd.concat([st.session_state.db, pd.DataFrame([yeni_ilan])], ignore_index=True)
                
                # Görseli hafızaya kaydetme
                if data['image']:
                    st.session_state.ilan_gorselleri[ilan_no] = data['image']
                
                st.success("İlan başarıyla analiz edildi ve listeye eklendi!")
                st.balloons()
            else:
                st.error("Site bot korumasına takıldı veya bilgiler çekilemedi. Lütfen linki kontrol edin.")

# --- 5. PROFESYONEL DASHBOARD (Karşılaştırma) ---
if not st.session_state.ilan_verileri.empty:
    st.divider()
    st.subheader("📊 İlan Karşılaştırma Dashboard'u")
    
    # Kıyaslanacak özellikleri seçme
    features = st.multiselect("Kıyaslanacak Özellikleri Seçin:", 
                                ["Fiyat (TL)", "m2 (Brüt)", "m2 Fiyatı", "Oda Sayısı", "Bina Yaşı"],
                                default=["Fiyat (TL)", "m2 Fiyatı", "Oda Sayısı"])
    
    # Yan Yana Kıyaslama Kartları
    # Her ilan için bir sütun oluşturuyoruz
    num_ilans = len(st.session_state.ilan_verileri)
    cols = st.columns(num_ilans)
    
    for i, (index, row) in enumerate(st.session_state.ilan_verileri.iterrows()):
        ilan_no = row['İlan No']
        
        with cols[i]:
            st.markdown(f"### {ilan_no}")
            
            # 1. Görsel Gösterimi (Eğer varsa)
            if ilan_no in st.session_state.ilan_gorselleri:
                st.image(st.session_state.ilan_gorselleri[ilan_no], use_column_width=True)
            else:
                st.info("Görsel Yok")
                
            # 2. Seçili Özelliklerin Gösterimi
            for feature in features:
                st.metric(label=feature, value=row[feature])
            
            # 3. İlan Linki
            st.markdown(f"[İlana Git]({row['Link']})")

    # Temizleme Butonu
    st.divider()
    if st.button("Tüm Listeyi Sıfırla"):
        st.session_state.ilan_verileri = pd.DataFrame(columns=[
            "İlan No", "Tarih", "Başlık", "Fiyat (TL)", "m2 (Brüt)", "m2 Fiyatı", "Oda Sayısı", "Bina Yaşı", "Isıtma", "Link"
        ])
        st.session_state.ilan_gorselleri = {}
        st.rerun()

else:
    st.info("Henüz kıyaslanacak ilan eklenmemiş. Yukarıdaki alanı kullanarak başlayın.")
