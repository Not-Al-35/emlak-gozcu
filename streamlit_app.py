import streamlit as st
import pandas as pd
import cloudscraper
from bs4 import BeautifulSoup
import re
from datetime import datetime
from PIL import Image
from io import BytesIO
import requests

# --- 1. KONFİGÜRASYON ---
st.set_page_config(page_title="Emlak Gözcü v2.1", layout="wide")

# --- 2. HAFIZA YÖNETİMİ ---
if 'ilan_verileri' not in st.session_state:
    st.session_state.ilan_verileri = pd.DataFrame(columns=[
        "İlan No", "Tarih", "Başlık", "Fiyat (TL)", "m2 (Brüt)", "m2 Fiyatı", "Oda Sayısı", "Bina Yaşı", "Link"
    ])
if 'ilan_gorselleri' not in st.session_state:
    st.session_state.ilan_gorselleri = {}

# --- 3. VERİ VE GÖRSEL ÇEKİCİ (SCRAPER) ---
def scrape_all_details(url):
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
    try:
        response = scraper.get(url, timeout=15)
        if response.status_code != 200: return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        text_content = soup.get_text()
        
        # Sayıları temizleme (Fiyat ve m2)
        prices = re.findall(r'(\d{1,3}(?:\.\d{3})+)[\s]?TL', text_content)
        m2s = re.findall(r'(\d{2,4})[\s]?m²', text_content)
        rooms = re.findall(r'(\d\+\d)', text_content)
        
        fiyat = int(prices[0].replace(".", "")) if prices else 0
        m2 = int(m2s[0]) if m2s else 1
        oda = rooms[0] if rooms else "Bilinmiyor"
        title = soup.title.string.split("|")[0].strip() if soup.title else "İlan Detayı"

        # Görsel Bulma (og:image en garanti yoldur)
        img_url = None
        og_image = soup.find("meta", property="og:image")
        if og_image:
            img_url = og_image["content"]
        
        img_obj = None
        if img_url:
            try:
                img_res = requests.get(img_url, timeout=5)
                img_obj = Image.open(BytesIO(img_res.content))
                img_obj.thumbnail((300, 300)) # Dashboard için optimize et
            except:
                img_obj = None
                
        return {"title": title, "fiyat": fiyat, "m2": m2, "oda": oda, "image": img_obj}
    except:
        return None

# --- 4. ARAYÜZ ---
st.title("🏗️ Emlak Gözcü v2.1 | Karşılaştırma")

url_input = st.text_input("İlan Linkini Yapıştırın ve Enter'a Basın:")

if url_input:
    # Mükerrer kayıt kontrolü
    if url_input in st.session_state.ilan_verileri['Link'].values:
        st.info("Bu ilan zaten listenizde ekli.")
    else:
        with st.spinner('Veriler ve görsel analiz ediliyor...'):
            data = scrape_all_details(url_input)
            
            if data:
                m2_fiyat = int(data['fiyat'] / data['m2']) if data['m2'] > 0 else 0
                ilan_no = f"İlan #{len(st.session_state.ilan_verileri) + 1}"
                
                yeni_row = {
                    "İlan No": ilan_no,
                    "Tarih": datetime.now().strftime("%d/%m/%Y"),
                    "Başlık": data['title'],
                    "Fiyat (TL)": f"{data['fiyat']:,}",
                    "m2 (Brüt)": data['m2'],
                    "m2 Fiyatı": m2_fiyat,
                    "Oda Sayısı": data['oda'],
                    "Bina Yaşı": "Çekilemedi",
                    "Link": url_input
                }
                
                # HATANIN DÜZELTİLDİĞİ SATIR (st.session_state.db yerine ilan_verileri)
                st.session_state.ilan_verileri = pd.concat([st.session_state.ilan_verileri, pd.DataFrame([yeni_row])], ignore_index=True)
                
                if data['image']:
                    st.session_state.ilan_gorselleri[ilan_no] = data['image']
                
                st.success("İlan eklendi!")
            else:
                st.error("Veri çekilemedi. Site botu engellemiş olabilir.")

# --- 5. KARŞILAŞTIRMA DASHBOARD ---
if not st.session_state.ilan_verileri.empty:
    st.divider()
    
    # Kıyaslanacak sütunlar
    cols = st.columns(len(st.session_state.ilan_verileri))
    
    for i, (idx, row) in enumerate(st.session_state.ilan_verileri.iterrows()):
        with cols[i]:
            # Görsel
            ino = row['İlan No']
            if ino in st.session_state.ilan_gorselleri:
                st.image(st.session_state.ilan_gorselleri[ino], use_container_width=True)
            
            # Veriler
            st.subheader(ino)
            st.write(f"**{row['Fiyat (TL)']} TL**")
            st.write(f"📏 {row['m2 (Brüt)']} m²")
            st.write(f"💰 m²: {row['m2 Fiyatı']:,} TL")
            st.write(f"🏠 {row['Oda Sayısı']}")
            st.markdown(f"[İlana Git 🔗]({row['Link']})")

    if st.button("Tümünü Temizle"):
        st.session_state.ilan_verileri = pd.DataFrame(columns=st.session_state.ilan_verileri.columns)
        st.session_state.ilan_gorselleri = {}
        st.rerun

import streamlit as st

# Secrets içinden linki çekiyoruz
sheet_url = st.secrets["https://docs.google.com/spreadsheets/d/1qu7K65hDkGk5amJcW6rOGURtr5KncdK1sVQdgyblvo4/edit?usp=sharing"]

st.write(f"Bağlanılacak tablo: {sheet_url}")
