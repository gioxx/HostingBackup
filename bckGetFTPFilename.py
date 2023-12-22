from ftplib import FTP
import json
import os
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

# Ottengo le informazioni di connessione per il set di credenziali specificato
credentials = ftp_config[credentials_set_name]
server = credentials["host"]
ftp_username = credentials["ftp_username"]
ftp_password = credentials["ftp_password"]

# Connetto al server FTP
ftp = FTP(server)
ftp.login(ftp_username, ftp_password)

# Navigo nella directory principale del server FTP (dove cPanel solitamente appoggia il fullbackup)
ftp.cwd("/")

# Ottengo l'elenco di tutti i file nella directory
all_files = ftp.nlst()

# Ottengo il nome del file di backup salvato sul server e lo mando a video
for filename in all_files:
    if filename.startswith("backup-") and filename.endswith(".tar.gz"):
        print(filename)

# Chiudo la connessione FTP
ftp.quit()