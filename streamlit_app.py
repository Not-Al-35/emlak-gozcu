import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

# --- KONFİGÜRASYON ---
st.set_page_config(page_title="Emlak Gözcü v1.2", layout="wide")

# --- VERİ TABANI (Session State - Geçici Hafıza) ---
if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=["Tarih", "Mahalle", "Fiyat", "m2", "Birim_Fiyat", "Skor", "Link"])

# --- SCRAPER FONKSİYONU ---
def scrape_listing(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        html_content = soup.get_text()

        # Regex ile Fiyat ve m2 bulma (Çoğu sitede işe yarar genel bir yaklaşım)
        # Not: Sitelere özel class isimleri değiştiği için "sayı yakalama" metoduna gidiyoruz.
        prices = re.findall(r'(\d{1,3}(?:\.\d{3})*(?:\s?TL))', html_content)
        m2_candidates = re.findall(r'(\d{2,3})\s?m²', html_content)
        
        extracted_price = prices[0] if prices else "Bulunamadı"
        extracted_m2 = m2_candidates[0] if m2_candidates else "Bulunamadı"
        
        return {"price": extracted_price, "m2": extracted_m2}
    except Exception as e:
        return None

# --- ARAYÜZ ---
st.title("🏗️ Emlak Gözcü (Scout) v1.2")
st.markdown("Sadece ilan linkini yapıştırın, gerisini sisteme bırakın.")

# Link Giriş Alanı
url_input = st.text_input("İlan Linkini Buraya Yapıştırın:", placeholder="https://www.emlakjet.com/ilan/...")

if url_input:
    with st.spinner('Veriler analiz ediliyor...'):
        data = scrape_listing(url_input)
        
        if data:
            st.success("İlan verileri çekildi!")
            
            # Form içinde düzenleme imkanı (Hatalı çekilirse elle düzeltmek için)
            with st.form("kayit_formu"):
                col1, col2, col3 = st.columns(3)
                
                # Temizleme işlemi (TL ve nokta karakterlerini atma)
                clean_price = "".join(filter(str.isdigit, data['price'])) if data['price'] != "Bulunamadı" else 0
                clean_m2 = "".join(filter(str.isdigit, data['m2'])) if data['m2'] != "Bulunamadı" else 0

                mahalle = col1.selectbox("Bölge / Mahalle", list(REF_PRICES.keys()))
                fiyat = col2.number_input("Tespit Edilen Fiyat (TL)", value=int(clean_price) if clean_price else 0)
                m2 = col3.number_input("Tespit Edilen m2", value=int(clean_m2) if clean_m2 else 0)
                
                save_btn = st.form_submit_button("Analiz Et ve Veritabanına Ekle")
                
                if save_btn:
                    if fiyat > 0 and m2 > 0:
                        birim_fiyat = fiyat / m2
                        ref = REF_PRICES[mahalle]
                        skor = ((ref - birim_fiyat) / ref) * 100
                        
                        yeni_satir = {
                            "Tarih": datetime.now().strftime("%d/%m/%Y"),
                            "Mahalle": mahalle,
                            "Fiyat": f"{fiyat:,} TL",
                            "m2": m2,
                            "Birim_Fiyat": int(birim_fiyat),
                            "Skor": round(skor, 1),
                            "Link": url_input
                        }
                        
                        st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame([yeni_satir])], ignore_index=True)
                        st.balloons()
                    else:
                        st.error("Lütfen fiyat ve m2 bilgilerini kontrol edin.")
        else:
            st.error("Site bot korumasına takıldı veya bilgiler çekilemedi. Lütfen bilgileri manuel girin.")
            # Fallback (Hata durumunda manuel form)
            # (Buraya istersen manuel giriş formu ekleyebiliriz)

# --- TABLO VE FİLTRELEME ---
if not st.session_state.db.empty:
    st.divider()
    st.subheader("📊 Analiz Edilen Fırsatlar")
    
    # Renklendirme mantığı
    def color_skor(val):
        if val > 15: color = '#27ae60' # Kelepir
        elif val > 0: color = '#f1c40f' # Normal
        else: color = '#e74c3c' # Pahalı
        return f'background-color: {color}; color: white'

    st.dataframe(
        st.session_state.db.style.applymap(color_skor, subset=['Skor']),
        use_container_width=True
    )
    
    if st.button("Listeyi Temizle"):
        st.session_state.db = pd.DataFrame(columns=["Tarih", "Mahalle", "Fiyat", "m2", "Birim_Fiyat", "Skor", "Link"])
        st.rerun()
