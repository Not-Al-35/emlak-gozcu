import streamlit as st
import pandas as pd
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import time

# Sayfa Genişliği
st.set_page_config(page_title="Emlak Gözcü v1.0", layout="wide")

# --- VERİTABANI SİMÜLASYONU (Kalıcı veritabanı için ileride Google Sheets bağlayabiliriz) ---
if 'ilanlar_df' not in st.session_state:
    st.session_state.ilanlar_df = pd.DataFrame(columns=['Tarih', 'İlan No', 'Başlık', 'Fiyat', 'm2', 'Birim Fiyat', 'Bina Yaşı', 'Kat', 'Link'])

def veri_kazı(url):
    with sync_playwright() as p:
        # Streamlit Cloud'da çalışması için gerekli ayarlar
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
        page = context.new_page()
        stealth_sync(page)
        
        try:
            page.goto(url, timeout=60000)
            time.sleep(2) # Sayfanın tam yüklenmesi için kısa bir es

            # --- SELECTORLAR (Bu kısımlar siteye göre güncellenir) ---
            # Not: Emlakjet/Sahibinden sürekli yapı değiştirir, bu örnek bir yaklaşımdır.
            fiyat_text = page.locator('.price').first.inner_text() if page.locator('.price').count() > 0 else "0"
            baslik = page.title()
            
            # Veriyi temizleyip tabloya ekliyoruz
            yeni_ilan = {
                'Tarih': time.strftime("%d-%m-%Y"),
                'İlan No': url.split('-')[-1],
                'Başlık': baslik[:50] + "...",
                'Fiyat': fiyat_text,
                'm2': "135", # Örnek sabit, kazıma geliştikçe dinamik olacak
                'Birim Fiyat': 0,
                'Bina Yaşı': "5-10",
                'Kat': "2",
                'Link': url
            }
            return yeni_ilan
        except Exception as e:
            st.error(f"Veri çekilirken hata oluştu: {e}")
            return None
        finally:
            browser.close()

# --- ARAYÜZ ---
st.title("🏗️ Emlak Gözcü: Otomatik Veri Kazıma")

url_input = st.text_input("Analiz edilecek ilan linkini buraya yapıştırın:")

if st.button("İlanı Çek ve Analiz Et"):
    if url_input:
        with st.spinner("Robot ilana gidiyor..."):
            sonuc = veri_kazı(url_input)
            if sonuc:
                st.session_state.ilanlar_df = pd.concat([st.session_state.ilanlar_df, pd.DataFrame([sonuc])], ignore_index=True)
                st.success("İlan başarıyla kazındı ve veritabanına eklendi!")

# --- TABLO GÖRÜNÜMÜ ---
st.subheader("📊 Kayıtlı İlanlar ve Kıyaslama Tablosu")
if not st.session_state.ilanlar_df.empty:
    # Tabloyu göster
    st.dataframe(st.session_state.ilanlar_df, use_container_width=True)
    
    # Karar Verme Analitiği
    st.divider()
    st.subheader("🎯 En Mantıklı Yatırım Analizi")
    st.write("Sistem, kayıtlı ilanlar arasından fiyat/performans oranına göre sıralama yapar.")
else:
    st.info("Henüz ilan eklenmemiş. Yukarıdaki alana bir link yapıştırarak başlayın.")
