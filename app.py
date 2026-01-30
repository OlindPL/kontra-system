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
    # Zabezpieczenie przed pustym kluczem
    if "sk_test" not in STRIPE_SECRET_KEY:
        st.error("BŁĄD: Nie uzupełniono klucza Stripe w kodzie (linia 9).")
        return False
        
    try:
        # Pobieramy 20 ostatnich sesji płatności ze Stripe
        # To pozwala znaleźć wpłatę nawet jak klient chwilę zwlekał
        sessions = stripe.checkout.Session.list(limit=20)
        
        for session in sessions.data:
            # Sprawdzamy transakcje:
            # 1. Czy status to 'paid' (opłacone)
            # 2. Czy email klienta pasuje do tego, co wpisał w formularzu
            if session.customer_details and session.customer_details.email:
                stripe_email = session.customer_details.email.lower().strip()
                form_email = email_klienta.lower().strip()
                
                if stripe_email == form_email:
                    if session.payment_status == 'paid':
                        return True
        return False
    except Exception as e:
        st.error(f"Błąd połączenia ze Stripe: {e}")
        return False

# --- GENERATOR AI ---
def generuj_pelne_pismo(dane, strategia):
    if strategia == "GWARANCJA: Naprawa (Do Serwisu Producenta)":
        cel = "Zgłaszamy wadę z tytułu udzielonej GWARANCJI JAKOŚCI. Żądamy naprawy."
        tytul = "ZGŁOSZENIE REKLAMACYJNE Z GWARANCJI"
    elif strategia == "RĘKOJMIA: Naprawa / Wymiana":
        cel = "Żądamy doprowadzenia towaru do zgodności z umową poprzez WYMIANĘ na nowy lub NAPRAWĘ."
        tytul = "REKLAMACJA Z TYTUŁU RĘKOJMI"
    else: 
        cel = "Odstępujemy od umowy i żądamy zwrotu wpłaconych środków (Wada istotna)."
        tytul = "OŚWIADCZENIE O ODSTĄPIENIU OD UMOWY"

    prompt = f"""
    Jesteś profesjonalnym prawnikiem. Napisz skuteczne pismo reklamacyjne.
    
    DANE SPRAWY: {dane}
    STRATEGIA: {tytul}
    ŻĄDANIE KLIENTA: {cel}
    
    WYMAGANIA:
    - Język: Prawniczy, stanowczy, konkretny.
    - Format: Gotowy do druku (Miejscowość, Data, Nagłówki).
    - Uzasadnienie: Powołaj się na odpowiednie przepisy (Kodeks Cywilny lub Ustawa o Prawach Konsumenta).
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Błąd AI: {e}"

# --- INTERFEJS GRAFICZNY (FRONTEND) ---
st.set_page_config(page_title="KONTRA - Pisma Prawne", page_icon="⚖️")

# Nagłówek
st.title("⚖️ System KONTRA")
st.markdown("Profesjonalny generator pism reklamacyjnych.")

# Zmienna sesji (żeby pamiętał status płatności po odświeżeniu)
if 'oplacone' not in st.session_state:
    st.session_state['oplacone'] = False

# 1. FORMULARZ DANYCH (Zawsze widoczny)
with st.container():
    st.info("KROK 1: Uzupełnij dane do pisma.")
    
    col1, col2 = st.columns(2)
    with col1: 
        imie = st.text_input("Imię i Nazwisko")
    with col2: 
        # Email jest kluczowy - służy do weryfikacji płatności
        email = st.text_input("Twój adres EMAIL (Ważne!)")
        if email and "@" not in email:
            st.warning("Podaj poprawny adres email.")
    
    przedmiot = st.text_input("Nazwa produktu / usługi", placeholder="np. Buty Nike Air Max, Laptop Dell...")
    data_zakupu = st.date_input("Data zakupu")
    opis_wady = st.text_area("Opis wady / usterki", placeholder="Opisz dokładnie co się stało...")
    
    strategia = st.radio("Czego oczekujesz?", [
        "RĘKOJMIA: Naprawa / Wymiana (Zalecane)", 
        "RĘKOJMIA: Zwrot Pieniędzy (Odstąpienie)", 
        "GWARANCJA: Naprawa"
    ])

st.markdown("---")

# 2. SEKJA PŁATNOŚCI (Widoczna tylko jeśli NIE opłacono)
if not st.session_state['oplacone']:
    st.subheader("💳 KROK 2: Płatność i Pobranie")
    st.write("Koszt wygenerowania profesjonalnego pisma: **9.99 PLN**")
    
    col_pay, col_check = st.columns(2)
    
    with col_pay:
        # Tworzymy inteligentny link - sam wpisze maila klienta w Stripe
        if email and "@" in email:
            smart_link = f"{LINK_DO_PLATNOSCI}?prefilled_email={email}"
        else:
            smart_link = LINK_DO_PLATNOSCI
            
        st.link_button("👉 1. ZAPŁAĆ (9.99 PLN)", smart_link, type="primary", use_container_width=True)
    
    with col_check:
        if st.button("🔄 2. SPRAWDŹ WPŁATĘ", type="secondary", use_container_width=True):
            if not email or "@" not in email:
                st.error("❌ Najpierw wpisz swój adres email w formularzu powyżej!")
            elif "sk_test" not in STRIPE_SECRET_KEY:
                st.error("❌ BŁĄD KONFIGURACJI: Właściciel strony nie ustawił klucza Stripe.")
            else:
                with st.spinner("Łączę z systemem bankowym..."):
                    time.sleep(1) # Małe opóźnienie dla efektu
                    czy_zaplacil = sprawdz_czy_zaplacil(email)
                    
                    if czy_zaplacil:
                        st.session_state['oplacone'] = True
                        st.balloons()
                        st.success("✅ Płatność potwierdzona! Generuję dokument...")
                        st.rerun() # Przeładowanie strony, żeby pokazać wynik
                    else:
                        st.error("⛔ Nie znaleziono wpłaty dla tego adresu email.")
                        st.info("Upewnij się, że w płatności podałeś ten sam email co w formularzu.")

# 3. WYNIK (Widoczny TYLKO po opłaceniu)
if st.session_state['oplacone']:
    st.success("✅ DOKUMENT OPŁACONY I GOTOWY!")
    
    dane_calosc = f"Klient: {imie}, Email: {email}, Przedmiot: {przedmiot}, Data: {data_zakupu}, Opis wady: {opis_wady}"
    
    with st.spinner("Sztuczna Inteligencja pisze Twoje pismo..."):
        # Generowanie pisma
        gotowe_pismo = generuj_pelne_pismo(dane_calosc, strategia)
        
    st.subheader("📄 Twoje Pismo:")
    st.text_area("Skopiuj treść i wklej do Worda/Emaila:", value=gotowe_pismo, height=600)
    
    st.markdown("---")
    st.write("Chcesz wygenerować kolejne pismo dla innej sprawy?")
    if st.button("Nowa Sprawa (Wymaga nowej płatności)"):
        st.session_state['oplacone'] = False
        st.rerun()

st.caption("Nota prawna: Wygenerowane pismo jest wzorem stworzonym przez AI. Sprawdź je przed wysłaniem.")
