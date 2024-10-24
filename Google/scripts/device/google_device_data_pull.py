import json
import csv
import os
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from config import SERVICE_ACCOUNT_FILE, DELEGATED_ADMIN_EMAIL, base_dir

# Start timer
start_time = time.time()

# Get the current working directory dynamically
SERVICE_ACCOUNT_FILE = os.path.join(base_dir, '../../service/automatic-ou-user-sync-test-b35f84558a8c.json')
DELEGATED_ADMIN_EMAIL = 'thijs.klumpers@sgrbrussel.be'

# Scopes required for the API
SCOPES = ['https://www.googleapis.com/auth/admin.directory.device.chromeos.readonly']

# Create credentials using the service account
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

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


def write_to_csv(devices, filename):
    # Path to the CSV file in the csv folder
    csv_file_path = os.path.join(base_dir, f'../../csv/device/core/{filename}')

    # Define the CSV columns you want
    fields = ['deviceId', 'serialNumber', 'model', 'status', 'lastSync', 'assetId', 'location', 'lastKnownUserEmail']

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
                'lastKnownUserEmail': last_known_user_email
            }
            writer.writerow(device_data)

    print(f"CSV file written to: {csv_file_path}")


if __name__ == '__main__':
    chrome_devices = list_chrome_devices()
    write_to_csv(chrome_devices, 'all_google_device_data.csv')
    
print("Getting google device data took --- %s seconds ---" % (time.time() - start_time))