import os
import csv
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from config import SERVICE_ACCOUNT_FILE, DELEGATED_ADMIN_EMAIL, base_dir

# Start timer
start_time = time.time()

# Get the current working directory dynamically
csv_file_path = os.path.join(base_dir, '../../csv/device/matching_devices.csv')


# Load Google credentials from service account file
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=['https://www.googleapis.com/auth/admin.directory.device.chromeos']
)

# Delegate credentials
credentials = credentials.with_subject(DELEGATED_ADMIN_EMAIL)

service = build('admin', 'directory_v1', credentials=credentials)

# Function to check and update a device's assetId and location
def update_device(device_id, asset_id, location, serial_number):
    try:
        # Get the current device details
        device = service.chromeosdevices().get(customerId='my_customer', deviceId=device_id).execute()
        current_asset_id = device.get('annotatedAssetId', '')
        current_location = device.get('annotatedLocation', '')

        # Check if update is needed
        if current_asset_id == asset_id and current_location == location:
            print(f"No update needed for device with ID: {device_id}, Serial Number: {serial_number}")
            return False

        # Update the device
        updated_device = {
            'annotatedAssetId': asset_id,
            'annotatedLocation': location
        }
        service.chromeosdevices().patch(customerId='my_customer', deviceId=device_id, body=updated_device).execute()
        print(f"Successfully updated device with ID: {device_id}, Serial Number: {serial_number}")
        return True
    except Exception as e:
        print(f"Failed to update device with ID: {device_id}. Error: {e}")
        return False

# Read CSV file and update devices
updated_count = 0
total_count = 0
with open(csv_file_path, mode='r', encoding='utf-8') as csvfile:
    csv_reader = csv.DictReader(csvfile)
    for row in csv_reader:
        total_count += 1
        device_id = row['deviceId']
        asset_id = f"{row['Voornaam leerling']} {row['Achternaam leerling']}"
        location = row['Onderwijsinstelling']
        serial_number = row['Serial Number']
        if update_device(device_id, asset_id, location, serial_number):
            updated_count += 1

print(f"Total devices in list: {total_count}")
print(f"Total devices updated: {updated_count}")
print("Process finished in --- %s seconds ---" % (time.time() - start_time))
