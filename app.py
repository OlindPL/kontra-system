import streamlit as st
from openai import OpenAI
import datetime
import os

# --- KONFIGURACJA BIZNESOWA ---
# Tu wpisz swój link do płatności ze Stripe (na razie testowy)
LINK_DO_PLATNOSCI = "https://buy.stripe.com/test_..." 
# Kod, który klient otrzyma po wpłacie (możesz go zmieniać)
TAJNY_KOD = "KONTRA2026"

# --- KONFIGURACJA BEZPIECZEŃSTWA (SECRETS) ---
try:
    API_KEY = st.secrets["OPENAI_API_KEY"]
except:
    API_KEY = ""

client = OpenAI(api_key=API_KEY)

# --- LOGIKA SYSTEMU (BACKEND) ---
def generuj_pelne_pismo(dane, strategia):
    
    if strategia == "GWARANCJA: Naprawa (Do Serwisu Producenta)":
        cel = "Zgłaszamy wadę z tytułu udzielonej GWARANCJI JAKOŚCI. Żądamy naprawy zgodnie z warunkami karty gwarancyjnej."
        ton = "formalny"
        tytul = "ZGŁOSZENIE REKLAMACYJNE Z GWARANCJI"
        podstawa = "oświadczenia gwarancyjnego (karty gwarancyjnej)"
        
    elif strategia == "RĘKOJMIA: Naprawa / Wymiana (Do Sprzedawcy)":
        cel = "Żądamy doprowadzenia towaru do zgodności z umową poprzez WYMIANĘ na nowy lub NAPRAWĘ (Art. 43d ustawy o prawach konsumenta)."
        ton = "stanowczy, ale rzeczowy"
        tytul = "REKLAMACJA Z TYTUŁU NIEZGODNOŚCI TOWARU Z UMOWĄ"
        podstawa = "ustawy o prawach konsumenta"
        
    else: 
        cel = "Odstępujemy od umowy i żądamy zwrotu wpłaconych środków z powodu wady istotnej (Art. 43e ustawy o prawach konsumenta)."
        ton = "zimny, formalny i bezkompromisowy"
        tytul = "OŚWIADCZENIE O ODSTĄPIENIU OD UMOWY"
        podstawa = "ustawy o prawach konsumenta"

    prompt_systemowy = f"""
    Jesteś profesjonalnym prawnikiem. Twoim zadaniem jest napisanie pisma reklamacyjnego.
    
    STRUKTURA DOKUMENTU:
    1. Miejscowość i Data.
    2. Dane Nadawcy.
    3. Dane Adresata (Placeholder [DANE ADRESATA]).
    4. Tytuł: {tytul}.
    5. Treść:
       - Powołaj się na {podstawa}.
       - Opisz wadę profesjonalnym językiem.
       - Sformułuj żądanie: {cel}.
    6. Podpis.
    7. Załączniki.

    TON: {ton}.
    """
    
    nr_dowodu_tekst = dane['nr_dowodu'] if dane['nr_dowodu'] else "Inny dowód zakupu (w załączeniu)"

    dane_tekstowe = f"""
    MIEJSCOWOŚĆ I DATA: {dane['miasto']}, dnia {dane['dzisiejsza_data']}
    
    DANE NADAWCY:
    Imię i Nazwisko: {dane['imie']} {dane['nazwisko']}
    Adres zamieszkania: {dane['adres_pelny']}
    Telefon: {dane['telefon']}
    Email: {dane['email']}
    
    DANE O TOWARZE:
    Przedmiot: {dane['przedmiot']}
    Data zakupu: {dane['data_zakupu']}
    Numer dowodu zakupu: {nr_dowodu_tekst}
    
    OPIS PROBLEMU: {dane['opis_wady']}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt_systemowy},
                {"role": "user", "content": dane_tekstowe}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Błąd połączenia: {e}"

# --- INTERFEJS GRAFICZNY (FRONTEND) ---
st.set_page_config(page_title="KONTRA Pro", page_icon="⚖️")

st.title("⚖️ System KONTRA")
st.write("Profesjonalny generator pism reklamacyjnych.")

# 1. Dane Użytkownika
with st.expander("1. Dane Nadawcy (Twoje)", expanded=True):
    st.text_input("Data", value=str(datetime.date.today()), disabled=True)

    col1, col2 = st.columns(2)
    with col1:
        imie = st.text_input("Imię i Nazwisko")
    with col2:
        telefon = st.text_input("Numer telefonu")
    
    email = st.text_input("Adres Email")
    
    st.write("---")
    st.write("Adres zamieszkania:")
    
    col_ulica, col_kod, col_miasto = st.columns([2, 1, 1.5]) 
    
    with col_ulica:
        ulica = st.text_input("Ulica i numer", placeholder="ul. Długa 5/12")
    with col_kod:
        kod_pocztowy = st.text_input("Kod pocztowy", placeholder="00-000")
    with col_miasto:
        miasto = st.text_input("Miejscowość")

# 2. Dane Przedmiotu
with st.expander("2. Co reklamujemy?", expanded=True):
    przedmiot = st.text_input("Nazwa przedmiotu", placeholder="np. Laptop Dell XPS 15")
    
    col3, col4 = st.columns(2)
    with col3:
        data_zakupu = st.date_input("Data zakupu towaru")
    with col4:
        nr_dowodu = st.text_input("Numer paragonu/faktury (jeśli posiadasz)")

# 3. Opis Problemu
with st.expander("3. Wybór Strategii i Opis Wady", expanded=True):
    
    with st.expander("ℹ️ PORADNIK: Co wybrać? (Kliknij tutaj)", expanded=False):
        st.markdown("""
        **1. RĘKOJMIA (Najsilniejsza opcja)**
        * Pismo kierujesz do **SKLEPU**.
        * **Naprawa/Wymiana:** Bezpieczna opcja, sklep musi usunąć wadę.
        * **Zwrot Pieniędzy:** Opcja ostateczna, gdy wada jest istotna.
        
        **2. GWARANCJA (Opcja zapasowa)**
        * Pismo kierujesz do **SERWISU PRODUCENTA**.
        * Wybierz, gdy minęły 2 lata od zakupu lub sklep już nie istnieje.
        """)

    strategia = st.radio("Wybierz tryb reklamacji:", [
        "RĘKOJMIA: Naprawa / Wymiana (Do Sprzedawcy)", 
        "RĘKOJMIA: Zwrot Pieniędzy (Do Sprzedawcy)",
        "GWARANCJA: Naprawa (Do Serwisu Producenta)"
    ])
    
    if strategia == "GWARANCJA: Naprawa (Do Serwisu Producenta)":
        st.info("Wybrano Gwarancję: Pismo zostanie przygotowane dla serwisu gwarancyjnego.")
    elif strategia == "RĘKOJMIA: Naprawa / Wymiana (Do Sprzedawcy)":
        st.success("Wybrano Rękojmię: Żądasz od sklepu naprawy lub nowego towaru.")
    else:
        st.warning("Wybrano Rękojmię (Odstąpienie): Żądasz od sklepu zwrotu gotówki.")

    opis_wady = st.text_area("Opisz usterkę własnymi słowami:", height=100)

# 4. Dowody
with st.expander("4. Załączniki (Opcjonalne)", expanded=False):
    plik_paragon = st.file_uploader("Zdjęcie paragonu", type=['png', 'jpg', 'jpeg'])
    pliki_uszkodzen = st.file_uploader("Zdjęcia uszkodzeń", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

st.markdown("---")

# --- SEKCJA PŁATNOŚCI (PAYWALL) ---
st.subheader("💳 Finalizacja i Płatność")

col_info, col_pay = st.columns([2, 1])
with col_info:
    st.info("Aby wygenerować pismo, wymagany jest **Kod Dostępu**. \n\nOtrzymasz go natychmiast po opłaceniu usługi (BLIK / Przelew).")
    kod_uzytkownika = st.text_input("Wpisz otrzymany kod dostępu:", type="password", placeholder="Wpisz kod tutaj...")

with col_pay:
    st.write("Koszt usługi: **29.00 PLN**")
    st.link_button("👉 KUP KOD (BLIK)", LINK_DO_PLATNOSCI, type="primary", use_container_width=True)

st.markdown("---")

# --- ZGODY PRAWNE ---
zgoda_rodo = st.checkbox("✅ Akceptuję Regulamin i wyrażam zgodę na przetwarzanie danych.")

# --- PRZYCISK GENEROWANIA ---
if st.button("GENERUJ DOKUMENT PDF (PODGLĄD)", type="primary", use_container_width=True, disabled=not zgoda_rodo):
    
    # 1. SPRAWDZENIE KODU
    if kod_uzytkownika != TAJNY_KOD:
        st.error("⛔ BŁĄD: Nieprawidłowy kod dostępu! Musisz kupić kod, aby wygenerować pismo.")
    elif not imie or not telefon or not ulica or not kod_pocztowy or not miasto:
        st.error("❌ Uzupełnij wszystkie pola adresowe (Miejscowość, Ulica, Kod)!")
    else:
        pelny_adres_string = f"{ulica}, {kod_pocztowy} {miasto}"
        dane_formularza = {
            "miasto": miasto,
            "dzisiejsza_data": str(datetime.date.today()),
            "imie": imie,
            "nazwisko": "", 
            "adres_pelny": pelny_adres_string,
            "telefon": telefon,
            "email": email,
            "przedmiot": przedmiot,
            "data_zakupu": str(data_zakupu),
            "nr_dowodu": nr_dowodu,
            "opis_wady": opis_wady
        }
        
        with st.spinner('Prawnik AI przygotowuje dokument...'):
            wynik = generuj_pelne_pismo(dane_formularza, strategia)
            st.success("✅ Kod poprawny! Dokument gotowy!")
            
            st.subheader("1. Treść Pisma:")
            st.text_area("Tekst do skopiowania:", value=wynik, height=500)
            
            st.subheader("2. Załączniki do druku:")
            if plik_paragon: st.image(plik_paragon, caption="Dowód zakupu", width=300)
            if pliki_uszkodzen:
                cols = st.columns(len(pliki_uszkodzen))
                for idx, plik in enumerate(pliki_uszkodzen):
                    with cols[idx]: st.image(plik, caption=f"Foto {idx+1}", use_container_width=True)

            st.info("ℹ️ Instrukcja: Skopiuj treść pisma do Worda, a zdjęcia wydrukuj i dołącz do koperty.")

st.markdown("---")
st.caption("⚠️ **NOTA PRAWNA:** System wykorzystuje AI. Aplikacja nie świadczy pomocy prawnej. Weryfikacja treści należy do użytkownika.")
