import json
import csv
import os
import time
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Start timer
start_time = time.time()

# Load configuration from config.json
config_path = os.path.join(os.path.dirname(__file__), '../../service/config.json')
with open(config_path, 'r') as config_file:
    config = json.load(config_file)

SERVICE_ACCOUNT_FILE = config.get('SERVICE_ACCOUNT_FILE')
DELEGATED_ADMIN_EMAIL = config.get('DELEGATED_ADMIN_EMAIL')

# Define base_dir for your CSV files
base_dir = os.path.dirname(__file__)

# Scopes required for the API
SCOPES = ['https://www.googleapis.com/auth/admin.directory.device.chromeos.readonly']

# Create credentials using the service account
credentials = service_account.Credentials.from_service_account_file(
    os.path.join(base_dir, '../../service', SERVICE_ACCOUNT_FILE), scopes=SCOPES)


# Delegate the credentials to the admin
credentials = credentials.with_subject(DELEGATED_ADMIN_EMAIL)

# Build the service
service = build('admin', 'directory_v1', credentials=credentials)


def list_chrome_devices():
    devices = []
    request = service.chromeosdevices().list(customerId='my_customer')
    while request is not None:
        response = request.execute()
        devices.extend(response.get('chromeosdevices', []))
        request = service.chromeosdevices().list_next(previous_request=request, previous_response=response)
    return devices


def sanitize_domain(domain):
    # Remove special characters and domain extensions
    sanitized = re.sub(r'[^a-zA-Z0-9]', '', domain.split('.')[0])
    return sanitized


def write_to_csv(devices, filename):
    csv_file_path = os.path.join(base_dir, f'../../csv/device/core/{filename}')

    # Define the CSV columns you want
    fields = [
        'deviceId', 'serialNumber', 'model', 'status', 'lastSync', 
        'assetId', 'location', 'lastKnownUserEmail', 'orgUnitPath'
    ]

    # Open a CSV file to write with UTF-8 encoding
    with open(csv_file_path, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()

        for device in devices:
            # Parse device details
            recent_users = device.get('recentUsers', [])
            last_known_user_email = recent_users[0].get('email', 'N/A') if recent_users else 'N/A'

            device_data = {
                'deviceId': device.get('deviceId'),
                'serialNumber': device.get('serialNumber', 'N/A'),
                'model': device.get('model', 'N/A'),
                'status': device.get('status', 'N/A'),
                'lastSync': device.get('lastSync', 'N/A'),
                'assetId': device.get('annotatedAssetId', 'N/A'),
                'location': device.get('annotatedLocation', 'N/A'),
                'lastKnownUserEmail': last_known_user_email,
                'orgUnitPath': device.get('orgUnitPath', 'N/A')
            }
            writer.writerow(device_data)

    print(f"CSV file written to: {csv_file_path}")


if __name__ == '__main__':
    chrome_devices = list_chrome_devices()

    # Write all devices to a single CSV file
    write_to_csv(chrome_devices, 'all_google_device_data_all.csv')

    # Organize devices by domain
    domain_devices = {}
    for device in chrome_devices:
        org_unit_path = device.get('orgUnitPath', '')
        domain = org_unit_path.split('/')[1] if '/' in org_unit_path else 'root'
        sanitized_domain = sanitize_domain(domain)
        if sanitized_domain not in domain_devices:
            domain_devices[sanitized_domain] = []
        domain_devices[sanitized_domain].append(device)

    # Write devices to separate domain-specific files
    for domain, devices in domain_devices.items():
        file_name = f'all_google_device_data_{domain}.csv'
        if domain == '':
            file_name = 'all_google_device_data_root.csv'
        write_to_csv(devices, file_name)

print("Getting google device data took --- %s seconds ---" % (time.time() - start_time))
