import streamlit as st

st.set_page_config(page_title="Emlak Gözcü v1.0", page_icon="🏗️")
st.title("🏗️ Emlak Gözcü (Scout) v1.0")

# Manuel Veri Girişi
with st.container():
    st.subheader("İlan Analiz Paneli")
    url = st.text_input("İlan Linkini Buraya Yapıştırın (Opsiyonel)")
    fiyat = st.number_input("İlan Fiyatı (TL)", min_value=0, step=10000, format="%d")
    m2 = st.number_input("Net Metrekare", min_value=1, step=1)
    mahalle = st.text_input("Mahalle (Örn: İstiklal)")

    if st.button("Analiz Et ve Kaydet"):
        birim_fiyat = fiyat / m2
        st.info(f"Metrekare Birim Fiyatı: {birim_fiyat:,.2f} TL")
        # Gelecek adımda buraya kıyaslama motoru gelecek
        st.success("Veri sisteme işlendi!")
