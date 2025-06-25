import json
import csv
import os
import time
import re
from collections import defaultdict
from typing import List, Dict

from google.oauth2 import service_account
from googleapiclient.discovery import build

# ────────────────────────────────────────────────────────────────────────────────
# Configuration & Google API initialisation
# ────────────────────────────────────────────────────────────────────────────────

start_time = time.time()

# Load configuration from config.json
config_path = os.path.join(os.path.dirname(__file__), '../../service/config.json')
with open(config_path, 'r') as config_file:
    config = json.load(config_file)

SERVICE_ACCOUNT_FILE = config.get('SERVICE_ACCOUNT_FILE')
DELEGATED_ADMIN_EMAIL = config.get('DELEGATED_ADMIN_EMAIL')

# Directory that will hold the CSV output (already exists in your repo hierarchy)
base_dir = os.path.dirname(__file__)
output_dir = os.path.join(base_dir, '../../csv/device/core')

# Scopes required for the Admin SDK Directory API
SCOPES = ['https://www.googleapis.com/auth/admin.directory.device.chromeos.readonly']

# Create credentials using the service account and delegate to the super‑admin
credentials = service_account.Credentials.from_service_account_file(
    os.path.join(base_dir, '../../service', SERVICE_ACCOUNT_FILE), scopes=SCOPES
).with_subject(DELEGATED_ADMIN_EMAIL)

# Build the service client (Admin SDK → ChromeOS devices)
service = build('admin', 'directory_v1', credentials=credentials)

# Supported / expected device‑status values (API returns upper‑case values)
STATUSES_OF_INTEREST: List[str] = [
    'ACTIVE',          # "Provisioned" in Admin Console
    'PRE_PROVISIONED', # "Pre‑provisioned"
    'DEPROVISIONED',
    'DISABLED',
    'SUSPENDED'
]

ROOT_DISPLAY = '@root'  # what should appear in CSV when the device sits in the tenant root

# ────────────────────────────────────────────────────────────────────────────────
# Helper functions
# ────────────────────────────────────────────────────────────────────────────────

def list_chrome_devices() -> List[dict]:
    """Retrieve **all** ChromeOS devices for the customer (pagination handled)."""
    devices: List[dict] = []
    request = service.chromeosdevices().list(customerId='my_customer')
    while request is not None:
        response = request.execute()
        devices.extend(response.get('chromeosdevices', []))
        request = service.chromeosdevices().list_next(previous_request=request, previous_response=response)
    return devices


def sanitize_domain(domain: str) -> str:
    """Return a filesystem‑safe string for a school domain (first OU segment)."""
    return re.sub(r'[^a-zA-Z0-9]', '', domain.split('.')[0]) or 'root'


def write_raw_devices_csv(devices: List[dict], filename: str) -> None:
    """Dump raw device inventory to *filename* (with a fixed field order)."""
    csv_file_path = os.path.join(output_dir, filename)
    fields = [
        'deviceId', 'serialNumber', 'model', 'status', 'lastSync',
        'assetId', 'location', 'lastKnownUserEmail', 'orgUnitPath'
    ]

    with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()

        for device in devices:
            recent_users = device.get('recentUsers', [])
            last_known_user_email = recent_users[0].get('email', 'N/A') if recent_users else 'N/A'

            writer.writerow({
                'deviceId': device.get('deviceId'),
                'serialNumber': device.get('serialNumber', 'N/A'),
                'model': device.get('model', 'N/A'),
                'status': device.get('status', 'N/A'),
                'lastSync': device.get('lastSync', 'N/A'),
                'assetId': device.get('annotatedAssetId', 'N/A'),
                'location': device.get('annotatedLocation', 'N/A'),
                'lastKnownUserEmail': last_known_user_email,
                'orgUnitPath': device.get('orgUnitPath', 'N/A')
            })

    print(f"Raw CSV written → {csv_file_path}")


def write_status_summary(devices: List[dict],
                         filename: str = 'google_device_status_summary.csv') -> None:
    """Write a CSV with per-school counts *and* a TOTAL column / row."""

    # ── build the per-school counts ───────────────────────────────────────────
    summary: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for device in devices:
        org_unit_path: str = device.get('orgUnitPath', '')
        first_segment = org_unit_path.strip('/').split('/')[0] if org_unit_path else ''
        school_domain = first_segment or ROOT_DISPLAY          # '@root' if blank
        status = device.get('status', 'UNKNOWN').upper()
        summary[school_domain][status] += 1

    # ── figure out the status columns we actually need ───────────────────────
    encountered_statuses = {s for counts in summary.values() for s in counts}
    status_columns: List[str] = [s for s in STATUSES_OF_INTEREST
                                 if s in encountered_statuses]
    status_columns.extend(sorted(encountered_statuses.difference(status_columns)))

    # ── grand totals across all schools ───────────────────────────────────────
    grand_totals: Dict[str, int] = defaultdict(int)
    for school_counts in summary.values():
        for status, cnt in school_counts.items():
            grand_totals[status] += cnt
    grand_total_devices = sum(grand_totals.values())

    # ── write the CSV ─────────────────────────────────────────────────────────
    csv_file_path = os.path.join(output_dir, filename)
    with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)

        # header now includes an extra “TOTAL” column
        writer.writerow(['schoolDomain', *status_columns, 'TOTAL'])

        # grand-total row
        writer.writerow(['TOTAL',
                         *[grand_totals.get(s, 0) for s in status_columns],
                         grand_total_devices])

        # per-school rows
        for school in sorted(summary.keys()):
            row_total = sum(summary[school].get(s, 0) for s in status_columns)
            writer.writerow([
                school,
                *[summary[school].get(s, 0) for s in status_columns],
                row_total
            ])

    print(f"Status summary written → {csv_file_path}")

# ────────────────────────────────────────────────────────────────────────────────
# Main execution flow
# ────────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    devices = list_chrome_devices()

    # 1️⃣ Full inventory (all devices)
    write_raw_devices_csv(devices, 'all_google_device_data_all.csv')

    # 2️⃣ Per‑school inventory files
    buckets: Dict[str, List[dict]] = defaultdict(list)
    for device in devices:
        org_unit_path = device.get('orgUnitPath', '')
        first_segment = org_unit_path.strip('/').split('/')[0] if org_unit_path else ''
        domain_key = first_segment or 'root'
        buckets[sanitize_domain(domain_key)].append(device)

    for domain_key, bucket in buckets.items():
        fname = f'all_google_device_data_{domain_key}.csv'
        write_raw_devices_csv(bucket, fname)

    # 3️⃣ Status summary across **all** schools
    write_status_summary(devices)

    print("Google device export completed in %.2f s" % (time.time() - start_time))
