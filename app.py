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

# --- TREŚĆ REGULAMINU (HARDCODED) ---
REGULAMIN_TRESC = """
REGULAMIN USŁUGI "SYSTEM KONTRA" (Wersja MVP)

§1. Postanowienia Ogólne
1. Niniejszy regulamin określa zasady korzystania z generatora pism "KONTRA".
2. Usługa polega na automatycznym generowaniu wzoru pisma reklamacyjnego przy użyciu modelu językowego AI.

§2. Odpowiedzialność i Nota Prawna
1. Aplikacja NIE świadczy pomocy prawnej, poradnictwa prawnego ani nie zastępuje profesjonalnego prawnika.
2. Wygenerowane pismo jest jedynie WZOREM. Użytkownik zobowiązany jest do jego weryfikacji przed wysłaniem.
3. Operator serwisu nie ponosi odpowiedzialności za skutki prawne użycia wygenerowanego pisma ani za ewentualne błędy merytoryczne popełnione przez sztuczną inteligencję (hallucynacje AI).

§3. Płatności i Dostawa
1. Koszt wygenerowania jednego dokumentu wynosi 9,99 zł brutto.
2. Płatności obsługiwane są przez zewnętrznego operatora Stripe.

§4. Prawo odstąpienia od umowy
1. Zgodnie z art. 38 ustawy o prawach konsumenta, prawo odstąpienia od umowy zawartej na odległość NIE PRZYSŁUGUJE konsumentowi w odniesieniu do umów o dostarczanie treści cyfrowych, które nie są zapisane na nośniku materialnym, jeżeli spełnianie świadczenia rozpoczęło się za wyraźną zgodą konsumenta przed upływem terminu do odstąpienia od umowy i po poinformowaniu go przez przedsiębiorcę o utracie prawa odstąpienia od umowy.
"""

# --- KONFIGURACJA API ---
try:
    API_KEY = st.secrets["OPENAI_API_KEY"]
except:
    API_KEY = ""

client = OpenAI(api_key=API_KEY)
stripe.api_key = STRIPE_SECRET_KEY

# --- FUNKCJA SPRAWDZAJĄCA PŁATNOŚĆ ---
def sprawdz_czy_zaplacil(email_klienta):
    if "sk_test" not in STRIPE_SECRET_KEY:
        st.error("BŁĄD KRYTYCZNY: Brak klucza Stripe w kodzie!")
        return False
        
    try:
        sessions = stripe.checkout.Session.list(limit=20)
        for session in sessions.data:
            if session.customer_details and session.customer_details.email:
                stripe_email = session.customer_details.email.lower().strip()
                form_email = email_klienta.lower().strip()
                
                # Sprawdzamy czy zapłacone
                if stripe_email == form_email and session.payment_status == 'paid':
                    return True
        return False
    except Exception as e:
        st.error(f"Błąd połączenia z bankiem: {e}")
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
    - Ważne: Nie zmyślaj faktów, bazuj tylko na podanych danych.
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
st.caption("Generator Pism Prawnych AI")

# NOTA PRAWNA (WIDOCZNA NA GÓRZE)
st.warning("⚠️ **NOTA PRAWNA:** Aplikacja wykorzystuje Sztuczną Inteligencję. Wygenerowane pismo jest wzorem do edycji, a nie poradą prawną. Użytkownik korzysta z narzędzia na własną odpowiedzialność.")

# Zmienna sesji (status płatności)
if 'oplacone' not in st.session_state:
    st.session_state['oplacone'] = False

# ==========================================
# SEKJA 1: DANE KLIENTA I ADRESOWE
# ==========================================
with st.expander("1. Dane Nadawcy (Wymagane do pisma)", expanded=True):
    col1, col2 = st.columns(2)
    with col1: 
        imie = st.text_input("Imię i Nazwisko")
    with col2: 
        email = st.text_input("Twój adres EMAIL (Kluczowy do weryfikacji wpłaty!)")
    
    st.write("Adres zamieszkania (niezbędny w piśmie formalnym):")
    col_ulica, col_kod, col_miasto = st.columns([2, 1, 1])
    with col_ulica: ulica = st.text_input("Ulica i numer")
    with col_kod: kod = st.text_input("Kod pocztowy")
    with col_miasto: miasto = st.text_input("Miejscowość")

# ==========================================
# SEKJA 2: PORADNIK + DANE PRODUKTU
# ==========================================
with st.expander("2. Strategia i Opis Problemu", expanded=True):
    
    # --- MODUŁ EDUKACYJNY ---
    with st.expander("ℹ️ PORADNIK PRAWNY: Co wybrać? (Kliknij, aby rozwinąć)", expanded=False):
        st.markdown("""
        **1. RĘKOJMIA (Najsilniejsza opcja)**
        * Pismo kierujesz do **SKLEPU**.
        * Prawo chroni Cię przez 2 lata.
        * To sklep musi udowodnić, że wada nie istniała.
        
        **2. GWARANCJA (Opcja dodatkowa)**
        * Pismo kierujesz do **PRODUCENTA**.
        * Warunki ustala gwarant (często mniej korzystne niż rękojmia).
        """)

    przedmiot = st.text_input("Nazwa produktu/usługi", placeholder="np. Buty Nike, Laptop Dell")
    col_d1, col_d2 = st.columns(2)
    with col_d1: data_zakupu = st.date_input("Data zakupu")
    with col_d2: nr_dowodu = st.text_input("Nr paragonu (opcjonalnie)")
    
    strategia = st.radio("Tryb reklamacji:", [
        "RĘKOJMIA: Naprawa / Wymiana (Zalecane na start)", 
        "RĘKOJMIA: Zwrot Pieniędzy (Odstąpienie od umowy)", 
        "GWARANCJA: Naprawa (Serwis Producenta)"
    ])
    
    if "Naprawa" in strategia and "RĘKOJMIA" in strategia:
        st.info("✅ Dobry wybór. Żądamy przywrócenia towaru do zgodności z umową.")
    
    opis_wady = st.text_area("Opis wady", height=100, placeholder="Opisz dokładnie usterkę...")

# ==========================================
# SEKJA 3: ZAŁĄCZNIKI
# ==========================================
with st.expander("3. Załączniki (Zdjęcia/Paragon)", expanded=False):
    st.info("Załączone pliki zostaną dodane do podglądu gotowego dokumentu.")
    plik_paragon = st.file_uploader("Zdjęcie Paragonu", type=['png', 'jpg', 'jpeg', 'pdf'])
    pliki_uszkodzen = st.file_uploader("Zdjęcia Uszkodzeń", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

st.markdown("---")

# ==========================================
# SEKJA 4: PŁATNOŚĆ + REGULAMIN
# ==========================================
if not st.session_state['oplacone']:
    st.subheader("💳 Finalizacja i Płatność")
    
    # --- REGULAMIN I ZGODY (WAŻNE PRAWNIE) ---
    with st.expander("📄 Zobacz Regulamin Usługi (Kliknij)", expanded=False):
        st.markdown(REGULAMIN_TRESC)
    
    # Checkbox wymagany prawem przy sprzedaży treści cyfrowych
    zgoda_regulamin = st.checkbox("Akceptuję Regulamin serwisu.")
    zgoda_zwrot = st.checkbox("Wyrażam zgodę na natychmiastowe spełnienie świadczenia i przyjmuję do wiadomości, że tracę prawo do odstąpienia od umowy (zwrotu 14-dniowego) z momentem wygenerowania pisma.")
    
    wszystkie_zgody = zgoda_regulamin and zgoda_zwrot
    
    col_pay, col_check = st.columns(2)
    
    with col_pay:
        # Smart Link
        if email and "@" in email:
            smart_link = f"{LINK_DO_PLATNOSCI}?prefilled_email={email}"
        else:
            smart_link = LINK_DO_PLATNOSCI
        
        # Przycisk aktywny tylko po zaznaczeniu zgód
        st.link_button("👉 1. ZAPŁAĆ (9.99 PLN)", smart_link, type="primary", use_container_width=True, disabled=not wszystkie_zgody)
        if not wszystkie_zgody:
            st.caption("❌ Zaznacz obie zgody powyżej, aby przejść do płatności.")
    
    with col_check:
        if st.button("🔄 2. SPRAWDŹ WPŁATĘ", type="secondary", use_container_width=True, disabled=not wszystkie_zgody):
            if not email or "@" not in email:
                st.error("Wpisz poprawny email w sekcji 1!")
            elif "sk_test" not in STRIPE_SECRET_KEY:
                st.error("Błąd konfiguracji klucza Stripe.")
            else:
                with st.spinner("Łączę z bankiem..."):
                    time.sleep(1)
                    if sprawdz_czy_zaplacil(email):
                        st.session_state['oplacone'] = True
                        st.balloons()
                        st.success("Płatność potwierdzona! Generuję...")
                        st.rerun()
                    else:
                        st.error("Brak wpłaty dla tego adresu email.")

# ==========================================
# SEKJA 5: WYNIK (PO OPŁACENIU)
# ==========================================
if st.session_state['oplacone']:
    st.success("✅ DOKUMENT GOTOWY DO POBRANIA")
    
    dane_full = {
        "nadawca": imie,
        "adres": f"{ulica}, {kod} {miasto}",
        "email": email,
        "przedmiot": przedmiot,
        "data": str(data_zakupu),
        "wada": opis_wady
    }
    
    with st.spinner("AI pisze Twoje pismo..."):
        pismo = generuj_pelne_pismo(dane_full, strategia)
    
    st.subheader("📄 Treść Pisma")
    st.text_area("Możesz edytować treść tutaj:", value=pismo, height=600)
    
    # Wyświetlamy załączniki
    if plik_paragon or pliki_uszkodzen:
        st.divider()
        st.subheader("📎 Załączniki (Wydrukuj je)")
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
st.caption("System KONTRA v1.0 | Powered by OpenAI & Stripe")
