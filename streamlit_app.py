import streamlit as st
import pandas as pd
import cloudscraper
from bs4 import BeautifulSoup
import re
from datetime import datetime
import requests
from PIL import Image
from io import BytesIO

# --- 1. AYARLAR ---
st.set_page_config(page_title="Emlak Gözcü v3.0", layout="wide")

# --- 2. GOOGLE SHEETS BAĞLANTISI (Simüle Edilmiş - URL ile Bağlanabilir) ---
# Gerçek kullanımda: conn = st.connection("gsheets", type=GSheetsConnection)
def get_data():
    if "main_db" not in st.session_state:
        # Örnek sütun yapısı
        st.session_state.main_db = pd.DataFrame(columns=[
            "ID", "Liste", "Tarih", "Başlık", "Fiyat", "m2", "Oda", "Satıcı", "Link", "Fiyat_Gecmisi"
        ])
    return st.session_state.main_db

# --- 3. SCRAPER (Gelişmiş: Satıcı Bilgisi Dahil) ---
def advanced_scrape(url):
    scraper = cloudscraper.create_scraper()
    try:
        res = scraper.get(url, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        text = soup.get_text()
        
        # Veri Ayıklama
        prices = re.findall(r'(\d{1,3}(?:\.\d{3})+)[\s]?TL', text)
        fiyat = int(prices[0].replace(".", "")) if prices else 0
        
        # Satıcı Bilgisi (Emlakjet/Sahibinden özel class'ları değişkenlik gösterir)
        # Genel bir yaklaşım: "Emlak" veya "Danışman" kelimelerini ara
        satici = "Bilinmiyor"
        if "Emlak" in text or "Gayrimenkul" in text:
            satici = "Emlak Ofisi"
        elif "Sahibinden" in text:
            satici = "Sahibinden"

        return {
            "title": soup.title.string[:50] if soup.title else "İlan",
            "fiyat": fiyat,
            "m2": re.findall(r'(\d{2,4})[\s]?m²', text)[0] if re.findall(r'(\d{2,4})[\s]?m²', text) else 0,
            "oda": re.findall(r'(\d\+\d)', text)[0] if re.findall(r'(\d\+\d)', text) else "---",
            "satici": satici
        }
    except: return None

# --- 4. ARAYÜZ ---
st.title("🏙️ Emlak Gözcü v3.0 | CRM & Analiz")

# Kenar Çubuğu: Liste Yönetimi
st.sidebar.header("📁 Liste Yönetimi")
mevcut_listeler = ["Favoriler", "Acil Yatırımlık", "Serdivan Portföy", "Arsa/Arazi"]
secili_liste = st.sidebar.selectbox("Çalışılacak Listeyi Seçin", mevcut_listeler)

# İlan Ekleme Bölümü
with st.expander("➕ Yeni İlan Ekle / Analiz Et", expanded=True):
    url = st.text_input("İlan Linkini Yapıştır:")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔍 ANALİZ ET"):
            if url:
                with st.spinner("Veriler çekiliyor..."):
                    result = advanced_scrape(url)
                    if result:
                        st.session_state.temp_data = result
                        st.success(f"Analiz Başarılı: {result['title']}")
                        st.write(f"Fiyat: {result['fiyat']:,} TL | Satıcı: {result['satici']}")
                    else:
                        st.error("Veri çekilemedi.")
    
    with col_b:
        if st.button("💾 LİSTEYE KAYDET"):
            if "temp_data" in st.session_state:
                db = get_data()
                data = st.session_state.temp_data
                
                # Fiyat Değişimi Takibi (Eğer ilan varsa fiyatı güncelle, yoksa ekle)
                tarih_bugun = datetime.now().strftime("%d/%m/%Y")
                
                new_row = {
                    "ID": f"ID-{len(db)+1}",
                    "Liste": secili_liste,
                    "Tarih": tarih_bugun,
                    "Başlık": data['title'],
                    "Fiyat": data['fiyat'],
                    "m2": data['m2'],
                    "Oda": data['oda'],
                    "Satıcı": data['satici'],
                    "Link": url,
                    "Fiyat_Gecmisi": f"{tarih_bugun}: {data['fiyat']:,} TL"
                }
                st.session_state.main_db = pd.concat([db, pd.DataFrame([new_row])], ignore_index=True)
                st.toast("Veritabanı güncellendi ve kaydedildi!")

# --- 5. DASHBOARD & KIYASLAMA ---
db = get_data()
current_list_df = db[db['Liste'] == secili_liste]

if not current_list_df.empty:
    st.divider()
    st.subheader(f"📊 {secili_liste} İçeriği")
    
    # Çoklu Seçim ile Kıyaslama
    secilen_ilanlar = st.multiselect("Kıyaslamak istediğiniz ilanları seçin:", 
                                     current_list_df['Başlık'].tolist())
    
    if st.button("⚖️ SEÇİLİLERİ KIYASLA"):
        comparison_df = current_list_df[current_list_df['Başlık'].isin(secilen_ilanlar)]
        st.table(comparison_df[["Başlık", "Fiyat", "m2", "Oda", "Satıcı", "Fiyat_Gecmisi"]])

    # Ana Liste Tablosu
    st.dataframe(current_list_df, use_container_width=True)

    # Google Sheets'e Gönder (Manuel Tetikleme)
    if st.button("☁️ Google Sheets'e Yedekle"):
        st.info("Bu özellik için Google Service Account JSON dosyanızın tanımlı olması gerekir.")
        # Burada pandas_to_sheets fonksiyonu çalışacak
else:
    st.info(f"'{secili_liste}' listesinde henüz ilan yok.")

# Secrets içinden linki çekiyoruz
sheet_url = st.secrets["https://docs.google.com/spreadsheets/d/1qu7K65hDkGk5amJcW6rOGURtr5KncdK1sVQdgyblvo4/edit?usp=sharing"]

st.write(f"Bağlanılacak tablo: {sheet_url}")
