import streamlit as st
from openai import OpenAI
import stripe
import datetime
import time

# --- KONFIGURACJA BIZNESOWA ---

# 1. TU WKLEJ KLUCZ TAJNY ZE STRIPE (Secret Key - zaczyna się od sk_test_...)
STRIPE_SECRET_KEY = "sk_test_51SvI3pF4cgtAkW4Kl7EU9vD3f9RInde6kLP11kB66aCBQNRZuWtdelOPMKjBqBczaeYbBQhRkLNs9kptZTlxYmoJ00auxm37XP" 

# 2. TU WKLEJ LINK DO PŁATNOŚCI (Ten za 9.99 PLN)
LINK_DO_PLATNOSCI = "https://buy.stripe.com/test_6oU3cv4Ee00Jfic9yq0VO00"

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
    if "GWARANCJA" in strategia:
        tytul = "ZGŁOSZENIE REKLAMACYJNE Z GWARANCJI"
        podstawa = "oświadczenia gwarancyjnego (karty gwarancyjnej)"
    elif "Odstąpienie" in strategia: 
        tytul = "OŚWIADCZENIE O ODSTĄPIENIU OD UMOWY"
        podstawa = "art. 43e ust. 1 ustawy o prawach konsumenta (wada istotna)"
    else: 
        tytul = "REKLAMACJA Z TYTUŁU RĘKOJMI (NIEZGODNOŚĆ TOWARU)"
        podstawa = "art. 43d ustawy o prawach konsumenta"

    prompt = f"""
    Jesteś profesjonalnym prawnikiem. Napisz skuteczne pismo reklamacyjne.
    
    DANE NADAWCY: {dane['nadawca']}
    ADRES: {dane['adres']}
    PRZEDMIOT: {dane['przedmiot']} (Data zakupu: {dane['data']})
    OPIS WADY: {dane['wada']}
    STRATEGIA: {strategia}
    
    WYTYCZNE:
    - Styl: Formalny, stanowczy, prawniczy.
    - Podstawa prawna: Powołaj się na {podstawa}.
    - Format: Gotowy do druku (Miejscowość, Data, Nagłówki).
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
st.markdown("Profesjonalny generator pism reklamacyjnych z analizą prawną.")

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
    with col_ulica: ulica = st.text_input("Ulica i numer", placeholder="np. ul. Marszałkowska 1/5")
    with col_kod: kod = st.text_input("Kod pocztowy", placeholder="00-000")
    with col_miasto: miasto = st.text_input("Miejscowość")

# ==========================================
# SEKJA 2: PORADNIK + DANE PRODUKTU
# ==========================================
with st.expander("2. Strategia i Opis Problemu", expanded=True):
    
    # --- PRZYWRÓCONY MODUŁ EDUKACYJNY ---
    with st.expander("ℹ️ PORADNIK PRAWNY: Co wybrać? (Kliknij, aby rozwinąć)", expanded=False):
        st.markdown("""
        **1. RĘKOJMIA (Najsilniejsza opcja)**
        * Pismo kierujesz do **SKLEPU**.
        * Prawo chroni Cię przez 2 lata.
        * To sklep musi udowodnić, że wada nie istniała.
        
        **2. GWARANCJA (Opcja dodatkowa)**
        * Pismo kierujesz do **PRODUCENTA**.
        * Warunki ustala gwarant (często mniej korzystne niż rękojmia).
        * Wybierz tylko, gdy minęła rękojmia lub sklep upadł.
        """)

    przedmiot = st.text_input("Nazwa produktu/usługi", placeholder="np. Buty Nike, Laptop Dell, Remont łazienki")
    col_d1, col_d2 = st.columns(2)
    with col_d1: data_zakupu = st.date_input("Data zakupu")
    with col_d2: nr_dowodu = st.text_input("Nr paragonu (opcjonalnie)")
    
    # Wybór z wyjaśnieniami
    strategia = st.radio("Czego żądamy?", [
        "RĘKOJMIA: Naprawa / Wymiana (Zalecane na start)", 
        "RĘKOJMIA: Zwrot Pieniędzy (Odstąpienie od umowy)", 
        "GWARANCJA: Naprawa (Serwis Producenta)"
    ])
    
    # Dynamiczne podpowiedzi (Feedback dla usera)
    if "Naprawa / Wymiana" in strategia:
        st.info("✅ Dobry wybór. W pierwszej kolejności żądamy przywrócenia towaru do zgodności z umową.")
    elif "Zwrot Pieniędzy" in strategia:
        st.warning("⚠️ Uwaga: Odstąpienie od umowy jest skuteczne od razu tylko przy WADZIE ISTOTNEJ lub jeśli sklep już raz naprawiał towar.")
    else:
        st.info("ℹ️ Wybrano Gwarancję. Pamiętaj, że warunki zależą od karty gwarancyjnej, a nie ustawy.")

    opis_wady = st.text_area("Opis wady", height=100, placeholder="Opisz dokładnie usterkę. Np. 'Po 2 miesiącach użytkowania podeszwa w prawym bucie odkleiła się na długości 5cm. Towar był użytkowany zgodnie z przeznaczeniem.'")

# ==========================================
# SEKJA 3: ZAŁĄCZNIKI
# ==========================================
with st.expander("3. Załączniki (Zdjęcia/Paragon)", expanded=False):
    st.info("Dodaj zdjęcia teraz. Zostaną one dołączone do podglądu, abyś mógł je wydrukować razem z pismem.")
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
    
    # Wyświetlamy załączniki
    if plik_paragon or pliki_uszkodzen:
        st.divider()
        st.subheader("📎 Załączniki (Do druku)")
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
