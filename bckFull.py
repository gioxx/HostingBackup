from ftplib import FTP
from tqdm import tqdm  # Importo la libreria tqdm per disegnare la barra di avanzamento nel terminale durante il download
import json
import os
import requests
import sys
import time

def download_callback(data):
    local_file.write(data)
    pbar.update(len(data))  # Aggiorno la barra di avanzamento

def get_first_backup_file(ftp):
    file_list = ftp.nlst()
    for filename in file_list:
        if filename.startswith("backup-") and filename.endswith(".tar.gz"):
            return filename
    return None

def countdown(seconds,pre):
    while seconds > 0:
        sys.stdout.write(f"\r{pre} {seconds}s before rechecking")
        sys.stdout.flush()
        time.sleep(1)
        seconds -= 1
    print("")

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

# Impostazioni
credentials = ftp_config[credentials_set_name]
if credentials["host"].startswith("ftp."):
    cpanel_host = credentials["host"][4:]
else:
    cpanel_host = credentials["host"]
api_token = credentials["cpanel_api_token"]
ftp_password = credentials["ftp_password"]
ftp_username = credentials["ftp_username"]
mail_to_notify = credentials["mail_to_notify"]
server = credentials["host"]
username = credentials["cpanel_username"]

api_url = f'https://{cpanel_host}:2083/execute/Backup/fullbackup_to_homedir'
destination_folder = os.path.join(credentials["backup_local_dest_folder"], server)

# Creazione dell'header e parametri della richiesta
headers = {'Authorization': f'cpanel {username}:{api_token}'}
params = {'email': mail_to_notify}

# Effettuo la richiesta API
response = requests.get(api_url, headers=headers, params=params)

if response.status_code == 200:
    output = response.json()
    print(json.dumps(output, indent=4))

    # Connetto al server FTP
    ftp = FTP(server)
    ftp.login(ftp_username, ftp_password)

    # Navigo nella directory principale del server FTP (dove cPanel solitamente appoggia il fullbackup)
    ftp.cwd("/")

    # Monitoro lo spazio FTP fino a quando non compare il file di backup
    previous_file_size = None
    print_backup_file = None
    while True:
        try:
            backup_file = get_first_backup_file(ftp)
            if backup_file:
                if print_backup_file != backup_file:
                    print_backup_file = backup_file
                    print(f"{backup_file} found.")

                # Verifico l'occupazione su disco del file
                file_size = ftp.size(backup_file)
                if file_size == previous_file_size:
                    print(f"Stable file size, exiting the loop and download {backup_file} to {destination_folder}.")
                    break
                else:
                    # print("File size has changed, waiting before rechecking.")
                    countdown(30,"File size has changed, waiting") # Attendo 30 secondi prima di ricontrollare se esiste il file di backup
                    previous_file_size = file_size

            else:
                print("No backup file found, waiting before rechecking.")

        except Exception as e:
            print("Error:", e)
    
        # countdown(30) # Attendo 30 secondi prima di ricontrollare se esiste il file di backup


    # Ottengo l'elenco di tutti i file nella directory
    all_files = ftp.nlst()

    # Mi assicuro che la cartella di destinazione esista
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    # Scarico i file e li cancello poi dal server
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
else:
    print(f'Error during API request. Status code: {response.status_code}')
