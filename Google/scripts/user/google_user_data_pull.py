import csv
import os
import time
from googleapiclient.discovery import build
from google.oauth2 import service_account
from config import SERVICE_ACCOUNT_FILE, DELEGATED_ADMIN_EMAIL,base_dir

start_time = time.time()

# Scope for reading user information from the directory
SCOPES = ['https://www.googleapis.com/auth/admin.directory.user.readonly']

# Authenticate using the service account
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
credentials = credentials.with_subject(DELEGATED_ADMIN_EMAIL)

# Build the Admin SDK service for managing users
service = build('admin', 'directory_v1', credentials=credentials)

def get_all_google_users():
    """Fetches all users from the domain."""
    results = []
    request = service.users().list(customer='my_customer', maxResults=500, orderBy='email')

    while request is not None:
        response = request.execute()
        results.extend(response.get('users', []))
        request = service.users().list_next(previous_request=request, previous_response=response)

    return results

def write_to_csv(users):
    """Writes user data to a CSV file with UTF-8 encoding."""
    # Path to the CSV file in the csv folder
    csv_file_path = os.path.join(base_dir, '../../csv/user/core/all_google_user_data.csv')

    # Define the CSV columns you want
    fields = ['primaryEmail', 'firstName', 'lastName', 'orgUnitPath', 'lastLoginTime', 'suspended', 'isAdmin']
    
    # Open a CSV file to write with UTF-8 encoding
    with open(csv_file_path, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()

        for user in users:
            # Parse user details
            user_data = {
                'primaryEmail': user.get('primaryEmail'),
                'firstName': user['name'].get('givenName', ''),
                'lastName': user['name'].get('familyName', ''),
                'orgUnitPath': user.get('orgUnitPath', ''),
                'lastLoginTime': user.get('lastLoginTime', 'Never'),
                'suspended': user.get('suspended', False),
                'isAdmin': user.get('isAdmin', False)
            }
            writer.writerow(user_data)

    print(f"CSV file written to: {csv_file_path}")


# Fetch the user data
users = get_all_google_users()

# Write the data to CSV
write_to_csv(users)

print(f"Successfully written {len(users)} users to all_google_user_data.csv")
print("Getting google user data took --- %s seconds ---" % (time.time() - start_time))