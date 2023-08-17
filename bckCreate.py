from ftplib import FTP
import json
import os
import requests
import sys

check_existent_backup = True  # Imposta su False per ignorare e creare un nuovo backup

def get_first_backup_file(ftp):
    file_list = ftp.nlst()
    for filename in file_list:
        if filename.startswith("backup-") and filename.endswith(".tar.gz"):
            return filename
    return None

# Controllo se è stato fornito il nome del set di credenziali come argomento
if len(sys.argv) < 2:
    print("Usage: python script.py credentials_set_name")
    sys.exit(1)

credentials_set_name = sys.argv[1]
script_dir = os.path.dirname(os.path.abspath(__file__))

# Carico le informazioni FTP dal file di configurazione
with open(os.path.join(script_dir, "ftp_config.json"), "r") as config_file:
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
username = credentials["cpanel_username"]
api_url = f'https://{cpanel_host}:2083/execute/Backup/fullbackup_to_homedir'
mail_to_notify = credentials["mail_to_notify"]

# Creazione dell'header e dei parametri della richiesta
headers = {'Authorization': f'cpanel {username}:{api_token}'}
params = {'email': mail_to_notify}

if check_existent_backup:
    server = credentials["host"]
    ftp_username = credentials["ftp_username"]
    ftp_password = credentials["ftp_password"]

    # Connetto al server FTP
    ftp = FTP(server)
    ftp.login(ftp_username, ftp_password)

    # Navigo nella directory principale del server FTP (dove cPanel solitamente appoggia il fullbackup) e verifico l'esistenza di un file di backup precedente
    ftp.cwd("/")
    print_backup_file = None
    backup_file = get_first_backup_file(ftp)
    if backup_file:
        if print_backup_file != backup_file:
            print_backup_file = backup_file
            print(f"{backup_file} already found, download the existing backup before creating another one. Exit the script")
            sys.exit(0)

# Effettuo la richiesta API
response = requests.get(api_url, headers=headers, params=params)

if response.status_code == 200:
    output = response.json()
    print(json.dumps(output, indent=4))
else:
    print(f'Error during API request. Status code: {response.status_code}')
