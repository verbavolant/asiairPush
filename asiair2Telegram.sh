#!/bin/bash

# Configurazione
SAMBA_SHARE="//server/percorso/share"      # Percorso della condivisione Samba (formato SMB)
MOUNT_POINT="/mnt/samba_share"            # Punto di montaggio locale
SUBDIR="ASIAIR"                           # Sottodirectory da controllare
CREDENTIALS_FILE="/percorso/credenziali/cred.txt"  # File con credenziali per Samba
TELEGRAM_BOT_TOKEN="INSERISCI_IL_TUO_BOT_TOKEN"
TELEGRAM_CHAT_ID="INSERISCI_LA_TUA_CHAT_ID"
LOG_FILE="/percorso/del/file/log_nuovi_file.log"  # File di log per tracciare i file inviati

# Assicurati che le directory e il file di log esistano
mkdir -p "$MOUNT_POINT"
touch "$LOG_FILE"

# Funzione per verificare se la condivisione è montata
is_mounted() {
    mountpoint -q "$MOUNT_POINT"
}

# Monta la condivisione Samba se non è già montata
mount_samba_share() {
    if ! is_mounted; then
        echo "La condivisione Samba non è montata. Montaggio in corso..."
        sudo mount -t cifs "$SAMBA_SHARE" "$MOUNT_POINT" -o credentials="$CREDENTIALS_FILE",vers=3.0
        if [ $? -eq 0 ]; then
            echo "Condivisione Samba montata con successo."
        else
            echo "Errore nel montaggio della condivisione Samba." >&2
            exit 1
        fi
    else
        echo "La condivisione Samba è già montata."
    fi
}

# Funzione per elaborare un file FIT e convertirlo in JPEG
process_fit_file() {
    local fit_file=$1
    local output_file="/tmp/$(basename "${fit_file%.fit}.jpg")"

    # Applica il debayering e converte in JPEG (usando dcraw o equivalente)
    echo "Elaborazione di $fit_file in $output_file..."
    if command -v dcraw &>/dev/null; then
        dcraw -c -6 "$fit_file" | convert - "$output_file"
    else
        echo "Errore: dcraw non trovato. Installalo con 'sudo apt install dcraw'." >&2
        exit 1
    fi

    echo "$output_file"
}

# Funzione per inviare un file a Telegram
send_to_telegram() {
    local file_path=$1
    echo "Invio $file_path a Telegram..."
    curl -s -F chat_id="$TELEGRAM_CHAT_ID" \
         -F document=@"$file_path" \
         "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendDocument"

    if [ $? -eq 0 ]; then
        echo "$file_path inviato con successo."
        return 0
    else
        echo "Errore nell'invio di $file_path." >&2
        return 1
    fi
}

# Trova i file nuovi con estensione .jpg e .fit
check_and_send_files() {
    TARGET_DIR="$MOUNT_POINT/$SUBDIR"
    
    if [ ! -d "$TARGET_DIR" ]; then
        echo "La sottodirectory $SUBDIR non esiste. Esco."
        exit 1
    fi

    # Trova file .jpg
    new_jpg_files=$(find "$TARGET_DIR" -type f -name "*.jpg" ! -exec grep -q "{}" "$LOG_FILE" \; -print)
    if [ -n "$new_jpg_files" ]; then
        echo "Trovati nuovi file JPG:"
        echo "$new_jpg_files"
        while IFS= read -r jpg_file; do
            send_to_telegram "$jpg_file" && echo "$jpg_file" >> "$LOG_FILE"
        done <<< "$new_jpg_files"
    fi

    # Trova file .fit
    new_fit_files=$(find "$TARGET_DIR" -type f -name "*.fit" ! -exec grep -q "{}" "$LOG_FILE" \; -print)
    if [ -n "$new_fit_files" ]; then
        echo "Trovati nuovi file FIT:"
        echo "$new_fit_files"
        while IFS= read -r fit_file; do
            # Elabora e invia il JPEG generato
            jpeg_file=$(process_fit_file "$fit_file")
            if send_to_telegram "$jpeg_file"; then
                echo "$fit_file" >> "$LOG_FILE"
                rm -f "$jpeg_file"
                echo "File temporaneo $jpeg_file eliminato."
            fi
        done <<< "$new_fit_files"
    fi
}

# Monta la condivisione Samba se necessario
mount_samba_share

# Controlla, elabora e invia i nuovi file
check_and_send_files
