import json
import os
import requests
import sys

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
api_url = f'https://{cpanel_host}:2083/execute/Backup/list_backups'

# Creazione dell'header
headers = {'Authorization': f'cpanel {username}:{api_token}'}

# Effettuo la richiesta API
response = requests.get(api_url, headers=headers)

if response.status_code == 200:
    output = response.json()
    print(json.dumps(output, indent=4))
else:
    print(f'Error during API request. Status code: {response.status_code}')
