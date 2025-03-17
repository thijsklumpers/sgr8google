import os
import csv
import time
import json
from collections import defaultdict
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Start the timer
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


def read_csv(file_path):
    """ Reads a CSV file and returns a list of dictionaries. """
    with open(file_path, mode='r', encoding='utf-8') as file:
        return list(csv.DictReader(file))


def normalize_domain(domain):
    """ Ensures the domain starts with an '@' symbol. """
    domain = domain.lower().strip()
    return domain if domain.startswith('@') else f"@{domain}"


def get_valid_admins(admins):
    """
    Extracts and normalizes valid admin emails from the `userPrincipalName` field.
    Returns a dictionary {domain: admin_email}.
    """
    valid_admins = {}
    for admin in admins:
        user_principal = admin.get('userPrincipalName', '').strip().lower()
        if user_principal.startswith('admin@'):
            domain = normalize_domain(user_principal.split('@')[-1])
            valid_admins[domain] = user_principal  # Store the valid admin email per domain

    return valid_admins


def get_group_members(group_email):
    """
    Retrieves all members of a group and their roles.
    Returns a dictionary {email: role}.
    """
    try:
        members = service.members().list(groupKey=group_email).execute()
        return {m['email'].lower(): m['role'] for m in members.get('members', [])}
    except Exception as e:
        print(f"Error retrieving members for {group_email}: {e}")
        return {}


def update_member_role(group_email, admin_email):
    """
    Updates the admin's role in the group to OWNER if they are already a MEMBER or MANAGER.
    """
    try:
        member_body = {"role": "OWNER"}
        service.members().update(groupKey=group_email, memberKey=admin_email, body=member_body).execute()
        return True
    except Exception as e:
        print(f"❌ Error updating admin {admin_email} to OWNER in {group_email}: {e}")
        return False


def add_admin_as_owner(group_email, admin_email, group_members):
    """
    Adds the admin as an owner of the group if they are not already an owner.
    If the admin is a MEMBER or MANAGER, updates their role to OWNER instead of adding them again.
    """
    try:
        if admin_email in group_members:
            current_role = group_members[admin_email]
            if current_role in ["MEMBER", "MANAGER"]:
                print(f"🔄 {group_email} → Admin ({admin_email}) is already in the group as {current_role}. Updating to OWNER.")
                return update_member_role(group_email, admin_email)
            elif current_role == "OWNER":
                print(f"✅ {group_email} → Admin ({admin_email}) is already an OWNER. Skipping.")
                return False

        # If the admin is not in the group, add them as an OWNER
        member_body = {"email": admin_email, "role": "OWNER"}
        service.members().insert(groupKey=group_email, body=member_body).execute()
        print(f"🔄 {group_email} → Added admin ({admin_email}) as owner.")
        return True

    except Exception as e:
        print(f"❌ Error adding admin {admin_email} to {group_email}: {e}")
        return False


def process_groups(admins, groups):
    """
    Processes groups and ensures the correct admin is set as an owner.
    Optimized for performance while logging each group status.
    """
    valid_admins = get_valid_admins(admins)

    print("\n🔎 Found Admins in CSV (From `userPrincipalName`):")
    for domain, admin_email in valid_admins.items():
        print(f"  ✅ {admin_email} (for {domain})")

    groups_by_domain = defaultdict(list)
    for group in groups:
        group_email = group.get('email', '').strip().lower()
        if group_email:
            domain = normalize_domain(group_email.split('@')[-1])
            groups_by_domain[domain].append(group_email)

    total_groups = sum(len(groups) for groups in groups_by_domain.values())
    groups_with_valid_admin = 0
    groups_fixed = 0
    domains_without_admin = []

    print("\n🔍 Processing Groups...\n")

    for domain, group_list in groups_by_domain.items():
        valid_admin_email = valid_admins.get(domain)

        if not valid_admin_email:
            domains_without_admin.append(domain)
            for group_email in group_list:
                print(f"⚠️ {group_email} → No valid admin for this domain. Skipping.")
            continue

        for group_email in group_list:
            group_members = get_group_members(group_email)

            if valid_admin_email in group_members and group_members[valid_admin_email] == "OWNER":
                groups_with_valid_admin += 1
                print(f"✅ {group_email} → Already has correct admin ({valid_admin_email}) as owner. Skipping.")
                continue

            if add_admin_as_owner(group_email, valid_admin_email, group_members):
                groups_fixed += 1

    print("\n🔎 Summary Report")
    print(f"📌 Total groups checked: {total_groups}")
    print(f"✅ Groups with valid admin as owner: {groups_with_valid_admin}")
    print(f"🔄 Groups fixed (admin added): {groups_fixed}")

    if domains_without_admin:
        print(f"⚠️ Domains without valid admin: {', '.join(domains_without_admin)}")


if __name__ == "__main__":
    print("🚀 Starting the script to manage group ownerships...")

    base_dir = os.path.join(os.path.dirname(__file__), '../../csv')

    admins = read_csv(os.path.join(base_dir, 'user/core/admin_google_user_data.csv'))
    groups = read_csv(os.path.join(base_dir, 'groups/core/all_google_group_data.csv'))

    process_groups(admins, groups)

    print(f"🏁 Script completed in {round(time.time() - start_time, 2)} seconds.")
