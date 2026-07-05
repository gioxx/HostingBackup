import logging
import time

import requests

log = logging.getLogger(__name__)

# Wait between retries on connectivity errors: 10 min, then 30 min.
_RETRY_WAIT_SECONDS = [600, 1800]


def request_backup(cpanel_host: str, username: str, token: str, mail: str) -> bool:
    url = f"https://{cpanel_host}:2083/execute/Backup/fullbackup_to_homedir"
    headers = {"Authorization": f"cpanel {username}:{token}"}

    attempts = len(_RETRY_WAIT_SECONDS) + 1
    for attempt in range(1, attempts + 1):
        try:
            resp = requests.get(url, headers=headers, params={"email": mail}, timeout=30)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if attempt == attempts:
                log.error("Backup request failed after %d attempt(s): %s", attempt, e)
                return False
            wait = _RETRY_WAIT_SECONDS[attempt - 1]
            log.warning(
                "Backup request connectivity error (attempt %d/%d): %s — retrying in %d minutes",
                attempt, attempts, e, wait // 60,
            )
            time.sleep(wait)
            continue

        if resp.status_code == 200:
            data = resp.json()
            log.info("Backup request accepted: %s", data)
            return True
        log.error("Backup request failed: HTTP %s", resp.status_code)
        return False

    return False
