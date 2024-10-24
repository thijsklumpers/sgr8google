import csv
import os
import time
from googleapiclient.discovery import build
from google.oauth2 import service_account
from config import SERVICE_ACCOUNT_FILE, DELEGATED_ADMIN_EMAIL,base_dir

start_time = time.time()

# Scopes for reading user and role information from the directory
SCOPES = [
    'https://www.googleapis.com/auth/admin.directory.user.readonly',
    'https://www.googleapis.com/auth/admin.directory.rolemanagement.readonly'
]

# Authenticate using the service account
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
credentials = credentials.with_subject(DELEGATED_ADMIN_EMAIL)

# Build the Admin SDK service for managing users and roles
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

def get_admin_users():
    """Fetches all users with admin roles from the domain."""
    admin_users = []
    request = service.roleAssignments().list(customer='my_customer', maxResults=100)

    while request is not None:
        response = request.execute()
        admin_users.extend(response.get('items', []))
        request = service.roleAssignments().list_next(previous_request=request, previous_response=response)

    return admin_users

def get_role_names():
    """Fetches all roles and their names from the domain."""
    roles = {}
    request = service.roles().list(customer='my_customer')

    while request is not None:
        response = request.execute()
        for role in response.get('items', []):
            roles[role['roleId']] = role['roleName']
        request = service.roles().list_next(previous_request=request, previous_response=response)

    return roles

def write_admins_to_csv(admin_users, roles):
    """Writes admin user data to a CSV file with UTF-8 encoding."""
    # Path to the CSV file in the csv folder
    csv_file_path = os.path.join(base_dir, '../../csv/user/core/admin_google_user_data.csv')

    # Define the CSV columns you want
    fields = ['roleName', 'userPrincipalName', 'suspended', 'orgUnitPath']

    # Fetch all users to get additional details
    all_users = {user['id']: user for user in get_all_google_users()}

    admin_data_list = []

    for admin in admin_users:
        user_id = admin.get('assignedTo')
        if not user_id or user_id not in all_users:
            # Skip entries without an assigned user or users not found in the user list
            continue
        user = all_users.get(user_id, {})

        # Parse admin details
        admin_data = {
            'roleName': roles.get(admin.get('roleId'), 'Unknown'),
            'userPrincipalName': user.get('primaryEmail', ''),
            'suspended': user.get('suspended', False),
            'orgUnitPath': user.get('orgUnitPath', '')
        }
        admin_data_list.append(admin_data)

    # Sort the data by role name
    admin_data_list = sorted(admin_data_list, key=lambda x: x['roleName'])

    # Open a CSV file to write with UTF-8 encoding
    with open(csv_file_path, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(admin_data_list)

    print(f"CSV file written to: {csv_file_path}")

    # Count the number of unique users in the admin data list
    unique_users = {data['userPrincipalName'] for data in admin_data_list}
    print(f"{len(admin_data_list)} roles assigned to {len(unique_users)} unique users")

# Fetch the role names
roles = get_role_names()

# Fetch the admin user data
admin_users = get_admin_users()

# Write the admin data to CSV
write_admins_to_csv(admin_users, roles)

print("Getting admin user data took --- %s seconds ---" % (time.time() - start_time))