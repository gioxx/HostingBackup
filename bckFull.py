from ftplib import FTP
from tqdm import tqdm
import json
import os
import requests
import sys
import time

def download_callback(data):
    """
    Callback per aggiornare la barra di avanzamento.
    """
    local_file.write(data)
    pbar.update(len(data))

def get_first_backup_file(ftp):
    """
    Ottiene il primo file di backup disponibile sul server FTP.
    """
    file_list = ftp.nlst()
    for filename in file_list:
        if filename.startswith("backup-") and filename.endswith(".tar.gz"):
            return filename
    return None

def countdown(seconds, pre):
    """
    Mostra un conto alla rovescia nel terminale.
    """
    while seconds > 0:
        sys.stdout.write(f"\r{pre} {seconds}s before checking again")
        sys.stdout.flush()
        time.sleep(1)
        seconds -= 1
    print("")

def resume_download(ftp, filename, local_filepath):
    """
    Scarica il file dal server FTP con supporto per il resume.
    """
    # Verifica se esiste un file locale parzialmente scaricato
    resume_position = 0
    if os.path.exists(local_filepath):
        resume_position = os.path.getsize(local_filepath)
    
    # Ottiene la dimensione del file remoto
    remote_file_size = ftp.size(filename)

    # Apre il file locale in modalità append
    with open(local_filepath, "ab") as local_file, tqdm(
        total=remote_file_size,
        initial=resume_position,
        unit="B",
        unit_scale=True,
        desc=filename
    ) as pbar:
        # Riprende il download
        ftp.retrbinary(
            f"RETR {filename}",
            lambda data: (local_file.write(data), pbar.update(len(data))),
            rest=resume_position
        )

def reliable_download(ftp, filename, local_filepath):
    """
    Gestisce il download con riconnessione automatica in caso di errore.
    """
    while True:
        try:
            resume_download(ftp, filename, local_filepath)
            print("Download completed successfully!")
            break
        except Exception as e:
            print(f"Error occurred: {e}. Retrying in 5 seconds...")
            time.sleep(5)
            ftp = FTP(server)
            ftp.login(ftp_username, ftp_password)

# Controlla se è stato fornito il nome del set di credenziali come argomento
if len(sys.argv) < 2:
    print("Usage: python script.py credentials_set_name")
    sys.exit(1)

credentials_set_name = sys.argv[1]
script_dir = os.path.dirname(os.path.abspath(__file__))

# Carica le informazioni FTP dal file di configurazione
with open(os.path.join(script_dir, "ftp_config.json"), "r") as config_file:
    ftp_config = json.load(config_file)

# Verifica se il set di credenziali specificato esiste nel file di configurazione
if credentials_set_name not in ftp_config:
    print(f"Error: Credentials set '{credentials_set_name}' not found in configuration.")
    sys.exit(1)

# Impostazioni
credentials = ftp_config[credentials_set_name]
server = credentials["host"]
ftp_username = credentials["ftp_username"]
ftp_password = credentials["ftp_password"]
mail_to_notify = credentials["mail_to_notify"]
time_to_wait = credentials["time_to_wait"]
cpanel_api_token = credentials["cpanel_api_token"]
cpanel_username = credentials["cpanel_username"]
destination_folder = os.path.join(credentials["backup_local_dest_folder"], server)

# Impostazioni: URL delle API cPanel
if server.startswith("ftp."):
    cpanel_host = server[4:]
else:
    cpanel_host = server
api_url = f'https://{cpanel_host}:2083/execute/Backup/fullbackup_to_homedir'
headers = {'Authorization': f'cpanel {cpanel_username}:{cpanel_api_token}'}
params = {'email': mail_to_notify}

# Controlla se esiste già un backup
ftp = FTP(server)
ftp.login(ftp_username, ftp_password)
ftp.cwd("/")
existing_backup_file = get_first_backup_file(ftp)

if not existing_backup_file:
    # Se non esiste un backup, lo richiede tramite API cPanel
    response = requests.get(api_url, headers=headers, params=params)
    if response.status_code == 200:
        output = response.json()
        print(json.dumps(output, indent=4))
        print("Backup request sent successfully. Waiting for backup to be generated...")
    else:
        print(f"Error during API request. Status code: {response.status_code}")
        sys.exit(1)

# Aspetta che il file di backup venga generato (fino a quando non si stabilizza la dimensione del file, che prendo come indicatore per capire quando ha terminato il backup)
previous_file_size = None
while True:
    backup_file = get_first_backup_file(ftp)
    if backup_file:
        print(f"Backup file {backup_file} found.")
        file_size = ftp.size(backup_file)
        if file_size == previous_file_size:
            print("Backup file size is stable. Proceeding with download.")
            break
        else:
            previous_file_size = file_size
            countdown(time_to_wait, "Backup file size is changing. Waiting")
    else:
        countdown(15, "No backup file found. Retrying")

# Verifica che la cartella di destinazione esista e scarica il file di backup
if not os.path.exists(destination_folder):
    os.makedirs(destination_folder)
local_filepath = os.path.join(destination_folder, backup_file)
reliable_download(ftp, backup_file, local_filepath)

# Elimina il file dal server e chiude la connessione FTP
try:
    ftp.delete(backup_file)
    print(f"{backup_file} successfully deleted from the server.")
except Exception as e:
    print(f"Error while deleting {backup_file}: {e}")

ftp.quit()
