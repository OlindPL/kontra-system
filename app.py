import streamlit as st
from openai import OpenAI
import stripe
import datetime
import time

# --- KONFIGURACJA API ---
try:
    API_KEY = st.secrets["OPENAI_API_KEY"]
except:
    API_KEY = ""

client = OpenAI(api_key=API_KEY)
stripe.api_key = STRIPE_SECRET_KEY

# --- FUNKCJA SPRAWDZAJĄCA PŁATNOŚĆ (BRAMKA) ---
def sprawdz_czy_zaplacil(email_klienta):
    if "sk_test" not in STRIPE_SECRET_KEY:
        st.error("BŁĄD: Brak klucza Stripe w kodzie!")
        return False
        
    try:
        sessions = stripe.checkout.Session.list(limit=20)
        for session in sessions.data:
            if session.customer_details and session.customer_details.email:
                stripe_email = session.customer_details.email.lower().strip()
                form_email = email_klienta.lower().strip()
                
                if stripe_email == form_email and session.payment_status == 'paid':
                    return True
        return False
    except Exception as e:
        st.error(f"Błąd połączenia ze Stripe: {e}")
        return False

# --- GENERATOR AI ---
def generuj_pelne_pismo(dane, strategia):
    if strategia == "GWARANCJA: Naprawa (Do Serwisu Producenta)":
        tytul = "ZGŁOSZENIE REKLAMACYJNE Z GWARANCJI"
        podstawa = "oświadczenia gwarancyjnego"
    elif strategia == "RĘKOJMIA: Naprawa / Wymiana":
        tytul = "REKLAMACJA Z TYTUŁU RĘKOJMI (NAPRAWA/WYMIANA)"
        podstawa = "ustawy o prawach konsumenta (niezgodność towaru z umową)"
    else: 
        tytul = "OŚWIADCZENIE O ODSTĄPIENIU OD UMOWY"
        podstawa = "ustawy o prawach konsumenta (wada istotna)"

    prompt = f"""
    Jesteś prawnikiem. Napisz pismo: {tytul}.
    
    DANE NADAWCY: {dane['nadawca']}
    ADRES: {dane['adres']}
    PRZEDMIOT: {dane['przedmiot']} (Data zakupu: {dane['data']})
    OPIS WADY: {dane['wada']}
    
    Treść ma być profesjonalna, powołaj się na {podstawa}.
    Uwzględnij miejsce na podpis.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Błąd AI: {e}"

# --- FRONTEND (WYGLĄD) ---
st.set_page_config(page_title="KONTRA Pro", page_icon="⚖️")

st.title("⚖️ System KONTRA")
st.markdown("Profesjonalny generator pism reklamacyjnych.")

# Zmienna sesji (status płatności)
if 'oplacone' not in st.session_state:
    st.session_state['oplacone'] = False

# ==========================================
# SEKJA 1: DANE KLIENTA I ADRESOWE
# ==========================================
with st.expander("1. Dane Nadawcy (Wymagane)", expanded=True):
    col1, col2 = st.columns(2)
    with col1: 
        imie = st.text_input("Imię i Nazwisko")
    with col2: 
        email = st.text_input("Twój adres EMAIL (Kluczowy do płatności!)")
    
    st.write("Adres (do nagłówka pisma):")
    col_ulica, col_kod, col_miasto = st.columns([2, 1, 1])
    with col_ulica: ulica = st.text_input("Ulica i numer")
    with col_kod: kod = st.text_input("Kod pocztowy")
    with col_miasto: miasto = st.text_input("Miejscowość")

# ==========================================
# SEKJA 2: DANE PRODUKTU
# ==========================================
with st.expander("2. Co reklamujemy?", expanded=True):
    przedmiot = st.text_input("Nazwa produktu/usługi")
    col_d1, col_d2 = st.columns(2)
    with col_d1: data_zakupu = st.date_input("Data zakupu")
    with col_d2: nr_dowodu = st.text_input("Nr paragonu/zamówienia (opcjonalnie)")
    
    opis_wady = st.text_area("Opis wady (Bądź dokładny)", height=100)
    
    strategia = st.radio("Czego żądamy?", [
        "RĘKOJMIA: Naprawa / Wymiana", 
        "RĘKOJMIA: Zwrot Pieniędzy", 
        "GWARANCJA: Naprawa"
    ])

# ==========================================
# SEKJA 3: ZAŁĄCZNIKI (TO CZEGO BRAKOWAŁO)
# ==========================================
with st.expander("3. Załączniki (Paragon / Zdjęcia)", expanded=False):
    st.info("Dodaj zdjęcia teraz. Zostaną one wyświetlone pod gotowym pismem, abyś mógł je wydrukować.")
    plik_paragon = st.file_uploader("Zdjęcie Paragonu", type=['png', 'jpg', 'jpeg', 'pdf'])
    pliki_uszkodzen = st.file_uploader("Zdjęcia Uszkodzeń", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

st.markdown("---")

# ==========================================
# SEKJA 4: PŁATNOŚĆ (BRAMKA)
# ==========================================
if not st.session_state['oplacone']:
    st.subheader("💳 Finalizacja")
    
    # Checkbox RODO
    zgoda = st.checkbox("Akceptuję regulamin i politykę prywatności.")
    
    col_pay, col_check = st.columns(2)
    
    with col_pay:
        # Smart Link (wpisuje maila automatycznie)
        if email and "@" in email:
            smart_link = f"{LINK_DO_PLATNOSCI}?prefilled_email={email}"
        else:
            smart_link = LINK_DO_PLATNOSCI
        
        st.link_button("👉 1. ZAPŁAĆ (9.99 PLN)", smart_link, type="primary", use_container_width=True, disabled=not zgoda)
    
    with col_check:
        if st.button("🔄 2. SPRAWDŹ WPŁATĘ", type="secondary", use_container_width=True, disabled=not zgoda):
            if not email or "@" not in email:
                st.error("Wpisz poprawny email w sekcji 1!")
            elif "sk_test" not in STRIPE_SECRET_KEY:
                st.error("Błąd konfiguracji klucza Stripe.")
            else:
                with st.spinner("Weryfikacja płatności w banku..."):
                    time.sleep(1)
                    if sprawdz_czy_zaplacil(email):
                        st.session_state['oplacone'] = True
                        st.balloons()
                        st.success("Płatność przyjęta!")
                        st.rerun()
                    else:
                        st.error("Nie znaleziono wpłaty. Upewnij się, że użyłeś tego samego maila.")

# ==========================================
# SEKJA 5: WYNIK (PO OPŁACENIU)
# ==========================================
if st.session_state['oplacone']:
    st.success("✅ DOKUMENT GOTOWY")
    
    # Pakujemy dane do AI
    dane_full = {
        "nadawca": imie,
        "adres": f"{ulica}, {kod} {miasto}",
        "email": email,
        "przedmiot": przedmiot,
        "data": str(data_zakupu),
        "wada": opis_wady
    }
    
    with st.spinner("Generowanie pisma..."):
        pismo = generuj_pelne_pismo(dane_full, strategia)
    
    st.subheader("📄 Treść Pisma")
    st.text_area("Skopiuj do Worda/Emaila:", value=pismo, height=600)
    
    # Wyświetlamy załączniki, żeby klient miał wszystko w jednym miejscu
    if plik_paragon or pliki_uszkodzen:
        st.divider()
        st.subheader("📎 Twoje Załączniki (Do druku)")
        if plik_paragon:
            st.image(plik_paragon, caption="Dowód Zakupu", width=300)
        if pliki_uszkodzen:
            cols = st.columns(3)
            for i, plik in enumerate(pliki_uszkodzen):
                with cols[i % 3]:
                    st.image(plik, caption=f"Uszkodzenie {i+1}", use_container_width=True)

    if st.button("Zacznij nową sprawę"):
        st.session_state['oplacone'] = False
        st.rerun()

st.markdown("---")
st.caption("Nota prawna: Generator AI. Sprawdź pismo przed wysłaniem.")
