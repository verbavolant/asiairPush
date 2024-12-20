import os
import shutil
import requests
from astropy.io import fits
import matplotlib.pyplot as plt
import numpy as np
import time

# dipendenze
# pip install astropy matplotlib requests

# Configurazione
SAMBA_SHARE = r"\\asiair\Udisk Images\ASIAIR\Autorun"  # Percorso dello share Samba
DESTINATION_BASE = r"e:\astro_auto" # Directory di destinazione per i file FIT copiati
TELEGRAM_BOT_TOKEN = "123123123:xxxxxxxxxxxxxxxxxxxxxxx"
TELEGRAM_CHAT_ID = "123123123123"
LOG_FILE = r"e:\astro_auto\astro_auto.log"       # File di log per tracciare i file inviati
TEMP_DIR = r"e:\astro_auto\temp\fit_to_jpeg"         # Directory temporanea per i file JPEG
INTERVAL = 7 * 60  # Intervallo in secondi (7 minuti)

# Assicurati che la directory temporanea e quella di destinazione esistano
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(DESTINATION_BASE, exist_ok=True)

# Funzione per inviare messaggi o file a Telegram
def send_to_telegram(text=None, file_path=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument" if file_path else f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {'chat_id': TELEGRAM_CHAT_ID}
    if text:
        data['text'] = text
    files = {'document': open(file_path, 'rb')} if file_path else None

    response = requests.post(url, data=data, files=files)
    if response.status_code == 200:
        print(f"Telegram: messaggio inviato con successo.")
        return True
    else:
        print(f"Errore nell'invio a Telegram: {response.text}")
        return False

# Funzione per leggere il log
def read_log():
    if not os.path.exists(LOG_FILE):
        return set()
    with open(LOG_FILE, 'r') as log:
        return set(log.read().splitlines())

# Funzione per aggiornare il log
def update_log(file_path):
    with open(LOG_FILE, 'a') as log:
        log.write(file_path + '\n')

# Funzione per convertire un file FIT in JPEG
def convert_fit_to_jpeg(fit_file):
    # Percorso del file JPEG temporaneo
    jpeg_file = os.path.join(TEMP_DIR, os.path.basename(fit_file).replace(".fit", ".jpg"))
    try:
        # Leggi il file FIT
        with fits.open(fit_file) as hdul:
            data = hdul[0].data
            if data is None:
                print(f"Errore: nessun dato trovato in {fit_file}")
                return None

        # Stretch automatico: calcola i percentili 1 e 99 per migliorare il contrasto
        vmin, vmax = np.percentile(data, [1, 99])
        normalized_data = np.clip((data - vmin) / (vmax - vmin), 0, 1)

        # Ridimensiona e salva l'immagine come JPEG
        original_height, original_width = normalized_data.shape
        new_height, new_width = original_height // 2, original_width // 2
        plt.figure(figsize=(new_width / 100, new_height / 100), dpi=100)
        plt.imshow(normalized_data, cmap='gray', origin='lower')
        plt.axis('off')
        plt.savefig(jpeg_file, bbox_inches='tight', pad_inches=0)
        plt.close()
        print(f"File convertito e ridimensionato: {fit_file} -> {jpeg_file}")
        return jpeg_file
    except Exception as e:
        print(f"Errore nella conversione di {fit_file}: {e}")
        return None

# Funzione per copiare i file FIT mantenendo la struttura
def copy_fit_file(fit_file):
    relative_path = os.path.relpath(fit_file, SAMBA_SHARE)
    destination_path = os.path.join(DESTINATION_BASE, relative_path)
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
    try:
        shutil.copy2(fit_file, destination_path)
        print(f"File copiato: {fit_file} -> {destination_path}")
        return destination_path
    except Exception as e:
        print(f"Errore nella copia di {fit_file}: {e}")
        return None

# Funzione principale per elaborare i file
def process_files():
    sent_files = read_log()

    # Cerca file FIT e JPEG
    for root, _, files in os.walk(SAMBA_SHARE):
        for file in files:
            file_path = os.path.join(root, file)

            # Ignora i file che iniziano con "Flat"
            if file.startswith("Flat"):
                print(f"Ignorato: {file}")
                continue

            # Processa file JPEG direttamente
            if file.endswith('.jpg') and file_path not in sent_files:
                if send_to_telegram(file_path=file_path):
                    update_log(file_path)

            # Converte file FIT in JPEG e copia
            elif file.endswith('.fit') and file_path not in sent_files:
                jpeg_file = convert_fit_to_jpeg(file_path)
                if jpeg_file:
                    send_to_telegram(file_path=jpeg_file)
                copy_fit_file(file_path)
                update_log(file_path)

# Ciclo Principale per Eseguire ogni 7 Minuti
if __name__ == "__main__":
    print("Avvio del servizio...")
    while True:
        print("Inizio elaborazione file...")
        process_files()
        print("Elaborazione completata. Attendo 7 minuti...")
        time.sleep(INTERVAL)
