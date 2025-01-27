import os
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Load configuration
config_path = os.path.join(os.path.dirname(__file__), '../../service/config.json')
with open(config_path, 'r') as config_file:
    config = json.load(config_file)

SERVICE_ACCOUNT_FILE = config.get('SERVICE_ACCOUNT_FILE')
DELEGATED_ADMIN_EMAIL = config.get('DELEGATED_ADMIN_EMAIL')

# OAuth scope for group management
SCOPES = ['https://www.googleapis.com/auth/admin.directory.group']

# Authenticate using the service account and delegated admin
credentials = service_account.Credentials.from_service_account_file(
    os.path.join(os.path.dirname(__file__), '../../service', SERVICE_ACCOUNT_FILE),
    scopes=SCOPES
)
credentials = credentials.with_subject(DELEGATED_ADMIN_EMAIL)

# Build the Admin SDK Directory service
service = build('admin', 'directory_v1', credentials=credentials)

def normalize_domain(domain):
    """
    Ensures the domain starts with an '@' symbol.
    """
    return domain if domain.startswith('@') else f"@{domain}"

def create_group(group_name, domain):
    """
    Creates a Google Group with the specified name and domain.
    """
    group_email = f"{group_name}{domain}"
    group_body = {
        "email": group_email,
        "name": group_name,
        "description": f"Group for {group_name} in domain {domain}"
    }
    
    try:
        group = service.groups().insert(body=group_body).execute()
        print(f"Group created successfully: {group['email']}")
    except Exception as e:
        if 'Entity already exists' in str(e):
            print(f"Group already exists: {group_email}")
        else:
            print(f"An error occurred while creating group {group_email}: {e}")

def create_groups_in_batch(domain, group_names):
    """
    Creates multiple Google Groups in the specified domain.
    """
    normalized_domain = normalize_domain(domain)
    for group_name in group_names:
        create_group(group_name, normalized_domain)

if __name__ == "__main__":
    print("Welcome to the Group Creation Script!")
    
    # Get the domain
    domain = input("Enter the domain: ").strip()
    
    # Get comma-separated group names
    print("Note: If you want to create multiple groups, separate their names with a comma (e.g., Group1, Group2, Group3).")
    group_names_input = input("Enter the group name(s): ").strip()
    
    # Split and clean up group names
    group_names = [name.strip() for name in group_names_input.split(',') if name.strip()]
    
    if group_names:
        print(f"Creating the following groups in the domain '{normalize_domain(domain)}':")
        for group in group_names:
            print(f"- {group}")
        create_groups_in_batch(domain, group_names)
    else:
        print("No valid group names provided. Exiting.")
