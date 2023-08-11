from ftplib import FTP
from tqdm import tqdm  # Importo la libreria tqdm per disegnare la barra di avanzamento nel terminale durante il download
import json
import os
import sys

def download_callback(data):
    local_file.write(data)
    pbar.update(len(data))  # Aggiorno la barra di avanzamento

# Controllo se è stato fornito il nome del set di credenziali come argomento
if len(sys.argv) < 2:
    print("Usage: python script.py credentials_set_name")
    sys.exit(1)

credentials_set_name = sys.argv[1]

# Carico le informazioni FTP dal file di configurazione
with open("ftp_config.json", "r") as config_file:
    ftp_config = json.load(config_file)

# Verifico se il set di credenziali specificato esiste nel file di configurazione
if credentials_set_name not in ftp_config:
    print(f"Error: Credentials set '{credentials_set_name}' not found in configuration.")
    sys.exit(1)

# Ottengo le informazioni di connessione per il set di credenziali specificato
credentials = ftp_config[credentials_set_name]
server = credentials["host"]
ftp_username = credentials["ftp_username"]
ftp_password = credentials["ftp_password"]
destination_folder = os.path.join(credentials["backup_local_dest_folder"], server)

# Connetto al server FTP
ftp = FTP(server)
ftp.login(ftp_username, ftp_password)

# Navigo nella directory principale del server FTP (dove cPanel solitamente appoggia il fullbackup)
ftp.cwd("/")

# Ottengo l'elenco di tutti i file nella directory
all_files = ftp.nlst()

# Mi assicuro che la cartella di destinazione esista
if not os.path.exists(destination_folder):
    os.makedirs(destination_folder)

# Scarico i file e li cancello dal server
for filename in all_files:
    if filename.startswith("backup-") and filename.endswith(".tar.gz"):
        local_filepath = os.path.join(destination_folder, filename)
        file_size = ftp.size(filename)  # Ottengo la dimensione del file

        # Utilizzo la callback per il feedback sull'avanzamento
        with open(local_filepath, "wb") as local_file, tqdm(total=file_size, unit="B", unit_scale=True, desc=filename) as pbar:
            ftp.retrbinary("RETR " + filename, download_callback)

        # Elimino il file dal server
        try:
            ftp.delete(filename)
            print(f"File {filename} successfully deleted.")
        except Exception as e:
            print(f"Error while deleting the file {filename}: {e}")

# Chiudo la connessione FTP
ftp.quit()