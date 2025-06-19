import csv
import os
import time
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account

# ──────────────────────────────────────────────────────────────
# 1.  Config & authentication
# ──────────────────────────────────────────────────────────────
start_time = time.time()

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '../../service/config.json')
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    cfg = json.load(f)

SERVICE_ACCOUNT_FILE = cfg['SERVICE_ACCOUNT_FILE']
DELEGATED_ADMIN_EMAIL = cfg['DELEGATED_ADMIN_EMAIL']
BASE_DIR = os.path.dirname(__file__)

SCOPES = ['https://www.googleapis.com/auth/admin.directory.user.readonly']

creds = (
    service_account.Credentials
    .from_service_account_file(
        os.path.join(os.path.dirname(__file__), '../../service', SERVICE_ACCOUNT_FILE),
        scopes=SCOPES
    )
    .with_subject(DELEGATED_ADMIN_EMAIL)
)

service = build('admin', 'directory_v1', credentials=creds)

# ──────────────────────────────────────────────────────────────
# 2.  Helpers
# ──────────────────────────────────────────────────────────────
def get_department(user: dict) -> str:
    """
    Extract the department name from users.organizations[].
    Returns an empty string if none is present.
    """
    for org in user.get('organizations', []):
        if org.get('primary'):
            return org.get('department', '')
    if user.get('organizations'):
        return user['organizations'][0].get('department', '')
    return ''

def normalize_last_login(ts: str | None) -> str:
    """
    Convert the Workspace “never logged in” sentinel value
    (1970-01-01T00:00:00.000Z) to the string 'noLogin'.
    """
    if not ts or ts.startswith('1970'):
        return 'noLogin'
    return ts

def get_all_google_users() -> list[dict]:
    """Fetch all users in the domain (projection='full' gives all attributes)."""
    all_users = []
    req = service.users().list(
        customer='my_customer',
        maxResults=500,
        orderBy='email',
        projection='full'
    )

    while req is not None:
        resp = req.execute()
        all_users.extend(resp.get('users', []))
        req = service.users().list_next(previous_request=req, previous_response=resp)

    return all_users


def write_to_csv(users: list[dict]) -> None:
    """Write selected attributes to CSV (UTF-8)."""
    csv_path = os.path.join(BASE_DIR, '../../csv/user/core/all_google_user_data.csv')
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    fields = [
        'primaryEmail', 'firstName', 'lastName', 'orgUnitPath',
        'department',                      # ← NEW COLUMN
        'lastLoginTime', 'suspended', 'isAdmin', 'updated'
    ]

    with open(csv_path, mode='w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()

        for user in users:
            writer.writerow({
                'primaryEmail':  user.get('primaryEmail', ''),
                'firstName':     user.get('name', {}).get('givenName', ''),
                'lastName':      user.get('name', {}).get('familyName', ''),
                'orgUnitPath':   user.get('orgUnitPath', ''),
                'department':    get_department(user),
                'lastLoginTime': normalize_last_login(user.get('lastLoginTime')),
                'suspended':     user.get('suspended', False),
                'isAdmin':       user.get('isAdmin', False),
                'updated':       user.get('updated', '')
            })

    print(f"CSV written ➜ {csv_path}")


# ──────────────────────────────────────────────────────────────
# 3.  Main
# ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    users = get_all_google_users()
    write_to_csv(users)

    print(f"Successfully wrote {len(users)} users to all_google_user_data.csv")
    print(f"Elapsed time: {(time.time() - start_time):.2f}s")
