import streamlit as st
import pandas as pd
import cloudscraper
from bs4 import BeautifulSoup
import re
from datetime import datetime

# --- 1. AYARLAR ---
st.set_page_config(page_title="Emlak Gözcü v3.1", layout="wide")

# --- 2. GOOGLE SHEETS BAĞLANTI MANTIĞI ---
# Not: Gerçek bağlantı için st.connection("gsheets") kullanılabilir. 
# Şimdilik yerel bir CSV ile kalıcılık sağlıyoruz (Cloud'da Sheets'e bağlayacağız).
DATA_FILE = "emlak_database.csv"

def get_data():
    try:
        return pd.read_csv(DATA_FILE)
    except:
        return pd.DataFrame(columns=["ID", "Liste", "Tarih", "Başlık", "Fiyat", "m2", "Oda", "Satıcı", "Link", "Fiyat_Gecmisi"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# --- 3. ANALİZ MOTORU ---
def advanced_scrape(url):
    scraper = cloudscraper.create_scraper()
    try:
        res = scraper.get(url, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        text = soup.get_text()
        
        prices = re.findall(r'(\d{1,3}(?:\.\d{3})+)[\s]?TL', text)
        fiyat = int(prices[0].replace(".", "")) if prices else 0
        m2 = re.findall(r'(\d{2,4})[\s]?m²', text)[0] if re.findall(r'(\d{2,4})[\s]?m²', text) else 0
        oda = re.findall(r'(\d\+\d)', text)[0] if re.findall(r'(\d\+\d)', text) else "---"
        
        satici = "Sahibinden" if "sahibinden" in url.lower() or "sahibinden" in text.lower() else "Emlak Ofisi"

        return {
            "title": soup.title.string[:60] if soup.title else "Yeni İlan",
            "fiyat": fiyat,
            "m2": m2,
            "oda": oda,
            "satici": satici
        }
    except: return None

# --- 4. ARAYÜZ ---
st.title("🏙️ Emlak Gözcü v3.1 | CRM & Analiz")

# Yan Panel: Liste Yönetimi
st.sidebar.header("📁 Liste Yönetimi")
mevcut_listeler = ["Favoriler", "Acil Yatırımlık", "Serdivan Portföy", "Arsa/Arazi"]
secili_liste = st.sidebar.selectbox("Çalışılacak Listeyi Seçin", mevcut_listeler)

# Veri Girişi
with st.expander("➕ Yeni İlan Ekle / Analiz Et", expanded=True):
    url = st.text_input("İlan Linkini Yapıştır:")
    col_a, col_b = st.columns(2)
    
    if url:
        if st.button("🔍 ANALİZ ET"):
            with st.spinner("Veriler analiz ediliyor..."):
                res = advanced_scrape(url)
                if res:
                    st.session_state.temp_data = res
                    st.info(f"Tespit Edilen: {res['title']} | Fiyat: {res['fiyat']:,} TL")
                else:
                    st.error("Site botu engelledi. Linki kontrol edin.")

        if st.button("💾 LİSTEYE KAYDET"):
            if "temp_data" in st.session_state:
                db = get_data()
                data = st.session_state.temp_data
                tarih = datetime.now().strftime("%d/%m/%Y")
                
                # Mevcut ilanı kontrol et (Fiyat Değişimi Takibi)
                if url in db['Link'].values:
                    idx = db[db['Link'] == url].index[0]
                    eski_fiyat = db.at[idx, 'Fiyat']
                    if eski_fiyat != data['fiyat']:
                        db.at[idx, 'Fiyat_Gecmisi'] = str(db.at[idx, 'Fiyat_Gecmisi']) + f" -> {tarih}: {data['fiyat']:,} TL"
                        db.at[idx, 'Fiyat'] = data['fiyat']
                    st.warning("İlan zaten vardı, fiyat geçmişi güncellendi!")
                else:
                    new_row = {
                        "ID": f"ID-{len(db)+1}", "Liste": secili_liste, "Tarih": tarih,
                        "Başlık": data['title'], "Fiyat": data['fiyat'], "m2": data['m2'],
                        "Oda": data['oda'], "Satıcı": data['satici'], "Link": url,
                        "Fiyat_Gecmisi": f"{tarih}: {data['fiyat']:,} TL"
                    }
                    db = pd.concat([db, pd.DataFrame([new_row])], ignore_index=True)
                    st.success("Yeni ilan kaydedildi!")
                
                save_data(db)
                st.rerun()

# --- 5. DASHBOARD & KIYASLAMA ---
db = get_data()
list_df = db[db['Liste'] == secili_liste]

if not list_df.empty:
    st.divider()
    st.subheader(f"📊 {secili_liste} Portföyü")
    
    # Seçili İlanları Kıyasla
    to_compare = st.multiselect("Kıyaslamak için ilan seçin:", list_df['Başlık'].unique())
    
    if to_compare:
        compare_df = list_df[list_df['Başlık'].isin(to_compare)]
        st.table(compare_df[["Başlık", "Fiyat", "m2", "Oda", "Satıcı", "Fiyat_Gecmisi"]])

    # Tüm Tablo
    st.dataframe(list_df, use_container_width=True)
    
    if st.button("🗑️ Listeyi Sıfırla"):
        db = db[db['Liste'] != secili_liste]
        save_data(db)
        st.rerun()
else:
    st.info(f"'{secili_liste}' listesi henüz boş.")
