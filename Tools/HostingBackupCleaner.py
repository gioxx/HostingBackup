from dotenv import load_dotenv
import os
import subprocess
import time

load_dotenv()
dry_run_mode = os.getenv("dry_run_mode") # Set to False to perform the deletion, True if you want to run the script in Dry Run
folder_path = os.getenv("folder_path")
excluded_folders = os.getenv("excluded_folders")
days_threshold = os.getenv("days_threshold")
sendlog_mailto = os.getenv("sendlog_mailto") # Enter the e-mail address to be notified
sendlog = os.getenv("sendlog") # Set to False to not send email when finished, True to send it (assuming there are files to be deleted)

def delete_old_files(folder_path, days_threshold, excluded_folders=None, dry_run=False):
    current_time = time.time()
    threshold_time = current_time - (days_threshold * 24 * 60 * 60)
    deleted_files = []
    file_to_delete = 0
    temp_log = ""

    for root, dirs, files in os.walk(folder_path, topdown=True):
        if excluded_folders is not None:
            dirs[:] = [d for d in dirs if os.path.join(root, d) not in excluded_folders]

        for file in files:
            if file.endswith('.tar.gz'):
                file_path = os.path.join(root, file)
                file_mtime = os.path.getmtime(file_path)
                if file_mtime < threshold_time:
                    if dry_run:
                        deleted_files.append(file_path)
                    else:
                        file_to_delete += 1
                        os.remove(file_path)
                        print(f"File deleted: {file_path}")
                        temp_log += f"File deleted: {file_path}\n"

    if sendlog:
        if file_to_delete > 0:
            sendlog_via_postfix = f"echo '{temp_log}' | mail -s 'Hosting Backup Cleaner log' {sendlog_mailto}"
            subprocess.run(sendlog_via_postfix, shell=True)

    if dry_run:
        print("DRY RUN ACTIVE - Files that would be deleted:")
        for file_path in deleted_files:
            print(file_path)

if __name__ == "__main__":
    delete_old_files(folder_path, days_threshold, excluded_folders, dry_run_mode)
