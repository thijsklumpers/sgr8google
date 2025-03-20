import os
import json
import time
from googleapiclient.discovery import build
from google.oauth2 import service_account

start_time = time.time()

# Load configuration
config_path = os.path.join(os.path.dirname(__file__), '../../service/config.json')
with open(config_path, 'r') as config_file:
    config = json.load(config_file)

SERVICE_ACCOUNT_FILE = config.get('SERVICE_ACCOUNT_FILE')
DELEGATED_ADMIN_EMAIL = config.get('DELEGATED_ADMIN_EMAIL')

# OAuth scope for group and group member management
SCOPES = [
    'https://www.googleapis.com/auth/admin.directory.group',
    'https://www.googleapis.com/auth/admin.directory.group.member'
]

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
        return group
    except Exception as e:
        if 'Entity already exists' in str(e):
            print(f"Group already exists: {group_email}")
            return None
        else:
            print(f"An error occurred while creating group {group_email}: {e}")
            return None

def add_admin_as_owner(group_email, admin_email):
    """
    Adds the admin as an owner of the group if they are not already an owner.
    """
    try:
        # Retrieve all members of the group
        members = service.members().list(groupKey=group_email).execute()
        
        # Check if the admin is already an owner
        if 'members' in members:
            for member in members['members']:
                if member['email'] == admin_email and member['role'] == 'OWNER':
                    print(f"Admin {admin_email} is already an owner of {group_email}.")
                    return
        
        # Add the admin as an owner
        member_body = {
            "email": admin_email,
            "role": "OWNER"
        }
        service.members().insert(groupKey=group_email, body=member_body).execute()
        print(f"Admin {admin_email} added as an owner of {group_email}.")
    except Exception as e:
        print(f"An error occurred while adding admin as owner: {e}")

def create_groups_in_batch(domain, group_names):
    """
    Creates multiple Google Groups in the specified domain and adds the admin as an owner.
    """
    normalized_domain = normalize_domain(domain)
    admin_email = f"admin{normalized_domain}"
    
    for group_name in group_names:
        group_email = f"{group_name}{normalized_domain}"
        
        # Check if the group already exists
        try:
            existing_group = service.groups().get(groupKey=group_email).execute()
            print(f"Group already exists: {group_email}")
        except Exception as e:
            if 'Not Found' in str(e):
                # Group does not exist, create it
                existing_group = create_group(group_name, normalized_domain)
            else:
                print(f"An error occurred while checking group {group_email}: {e}")
                continue
        
        # Add the admin as an owner if the group exists
        if existing_group:
            add_admin_as_owner(group_email, admin_email)

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

    print("Creating groups took --- %s seconds ---" % (time.time() - start_time))