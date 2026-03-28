import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- AYARLAR VE REFERANS VERİLER ---
# Buradaki rakamları Sakarya piyasasına göre güncelleyebilirsin
REFERANS_FIYATLAR = {
    "Serdivan - Mavi Durak": 35000,
    "Serdivan - Kampüs": 28000,
    "Erenler - Merkez": 22000,
    "Adapazarı - Yeni Camii": 25000,
    "Sapanca - Göl Kenarı": 55000
}

DATA_FILE = "ilanlar.csv"

# --- YARDIMCI FONKSİYONLAR ---
def veri_yukle():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=["Tarih", "Mahalle", "Fiyat", "m2", "Birim_Fiyat", "Skor", "Link"])

def veri_kaydet(df):
    df.to_csv(DATA_FILE, index=False)

# --- ARAYÜZ ---
st.set_page_config(page_title="Emlak Gözcü v1.1", layout="wide")
st.title("🏗️ Emlak Gözcü (Scout) v1.1")

# --- VERİ GİRİŞ ALANI ---
with st.expander("➕ Yeni İlan Ekle", expanded=True):
    with st.form("ilan_formu"):
        col1, col2 = st.columns(2)
        with col1:
            mahalle = st.selectbox("Mahalle Seçin", list(REFERANS_FIYATLAR.keys()))
            fiyat = st.number_input("İlan Fiyatı (TL)", min_value=0, step=100000)
        with col2:
            m2 = st.number_input("Brüt Metrekare", min_value=1, step=1)
            link = st.text_input("İlan Linki")
        
        submit = st.form_submit_button("Analiz Et ve Kaydet")

if submit:
    birim_fiyat = fiyat / m2
    ref_fiyat = REFERANS_FIYATLAR[mahalle]
    # Fırsat Skoru Hesabı
    skor = ((ref_fiyat - birim_fiyat) / ref_fiyat) * 100
    
    yeni_veri = {
        "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Mahalle": mahalle,
        "Fiyat": fiyat,
        "m2": m2,
        "Birim_Fiyat": round(birim_fiyat, 2),
        "Skor": round(skor, 1),
        "Link": link
    }
    
    df = veri_yukle()
    df = pd.concat([df, pd.DataFrame([yeni_veri])], ignore_index=True)
    veri_kaydet(df)
    st.success(f"İlan Kaydedildi! Fırsat Skoru: %{skor:.1f}")

# --- ANALİZ VE TABLO ---
df_goster = veri_yukle()

if not df_goster.empty:
    st.subheader("📊 Analiz Edilen İlanlar")
    
    # Renklendirme Fonksiyonu
    def highlight_skor(val):
        color = 'red'
        if val > 15: color = '#27ae60' # Koyu Yeşil
        elif val > 0: color = '#2ecc71' # Açık Yeşil
        elif val > -10: color = '#f1c40f' # Sarı
        return f'background-color: {color}'

    st.dataframe(df_goster.style.applymap(highlight_skor, subset=['Skor']))
else:
    st.info("Henüz ilan eklenmemiş. Yukarıdaki formu kullanarak başlayın.")
