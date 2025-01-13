import csv
import os
import time
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account

start_time = time.time()

# ------------------------------------------------------------------------------
# 1. Load Configuration
# ------------------------------------------------------------------------------
config_path = os.path.join(os.path.dirname(__file__), '../../service/config.json')
with open(config_path, 'r') as config_file:
    config = json.load(config_file)

SERVICE_ACCOUNT_FILE = config.get('SERVICE_ACCOUNT_FILE')
DELEGATED_ADMIN_EMAIL = config.get('DELEGATED_ADMIN_EMAIL')
base_dir = os.path.join(os.path.dirname(__file__))

# ------------------------------------------------------------------------------
# 2. Define the required OAuth Scope
#    For reading groups, use https://www.googleapis.com/auth/admin.directory.group.readonly
# ------------------------------------------------------------------------------
SCOPES = ['https://www.googleapis.com/auth/admin.directory.group.readonly']

# ------------------------------------------------------------------------------
# 3. Authenticate using the service account & delegated admin
# ------------------------------------------------------------------------------
credentials = service_account.Credentials.from_service_account_file(
    os.path.join(os.path.dirname(__file__), '../../service', SERVICE_ACCOUNT_FILE),
    scopes=SCOPES
)
credentials = credentials.with_subject(DELEGATED_ADMIN_EMAIL)

# ------------------------------------------------------------------------------
# 4. Build the Admin SDK Directory service (for Groups)
# ------------------------------------------------------------------------------
service = build('admin', 'directory_v1', credentials=credentials)

# ------------------------------------------------------------------------------
# 5. Function to retrieve all groups
# ------------------------------------------------------------------------------
def get_all_google_groups():
    """
    Fetches all groups from the domain.
    Uses pagination to ensure we retrieve all groups if there are more than maxResults.
    """
    results = []
    request = service.groups().list(
        customer='my_customer',   # 'my_customer' auto-detects your domain
        maxResults=200            # you can use a larger page size, e.g., 500 or 1000
    )

    while request is not None:
        response = request.execute()
        results.extend(response.get('groups', []))
        request = service.groups().list_next(previous_request=request, previous_response=response)

    return results

# ------------------------------------------------------------------------------
# 6. Write group data to CSV
# ------------------------------------------------------------------------------
def write_groups_to_csv(groups):
    """
    Writes group data to a CSV file with UTF-8 encoding.
    Modify the fields array based on the attributes you want to capture.
    """
    csv_file_path = os.path.join(base_dir, '../../csv/groups/core/all_google_group_data.csv')

    # Ensure the directory structure for the CSV file exists
    os.makedirs(os.path.dirname(csv_file_path), exist_ok=True)

    # Define the CSV columns (these are the group attributes you want to capture)
    fields = [
        'email', 
        'name', 
        'description', 
        'directMembersCount', 
        'adminCreated', 
        'aliases'
    ]

    with open(csv_file_path, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()

        for group in groups:
            # Build a dict for each row
            group_data = {
                'email': group.get('email', ''),
                'name': group.get('name', ''),
                'description': group.get('description', ''),
                'directMembersCount': group.get('directMembersCount', ''),
                'adminCreated': group.get('adminCreated', ''),
                # 'aliases' is a list of strings, so we can join them with commas
                'aliases': ', '.join(group.get('aliases', []))
            }
            writer.writerow(group_data)

    print(f"CSV file written to: {csv_file_path}")

# ------------------------------------------------------------------------------
# 7. Main execution: fetch groups, write to CSV
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    groups = get_all_google_groups()
    write_groups_to_csv(groups)

    print(f"Successfully written {len(groups)} groups to all_google_group_data.csv")
    print("Getting Google group data took --- %s seconds ---" % (time.time() - start_time))
