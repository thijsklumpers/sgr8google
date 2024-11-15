import subprocess
import os
import time
from colorama import Fore, Style, init

# Get the current working directory dynamically
base_dir = os.path.dirname(os.path.abspath(__file__))

# Initialize colorama
init()

start_time = time.time()

#---------------------------------#
# Build paths to the script files #
#---------------------------------#
# Users
google_user_data_pull_path = os.path.join(base_dir, '../scripts/user/google_user_data_pull.py')
csv_user_data_merge_path = os.path.join(base_dir, '../scripts/user/csv_user_data_merge.py')
move_suspended_users_path = os.path.join(base_dir, '../scripts/user/move_suspended_users.py')
move_leerling_to_ou_path = os.path.join(base_dir, '../scripts/user/move_leerling_to_ou.py')
move_admin_users_path = os.path.join(base_dir, '../scripts/user/move_admin_users.py')
move_users_to_ou_path = os.path.join(base_dir, '../scripts/user/move_users_to_ou.py')
csv_user_data_splitting_path = os.path.join(base_dir, '../scripts/user/csv_user_data_splitting.py')

# Devices
google_device_data_pull_path = os.path.join(base_dir, '../scripts/device/google_device_data_pull.py')
csv_device_data_merge_path = os.path.join(base_dir, '../scripts/device/csv_device_data_merge.py')
device_data_update_path = os.path.join(base_dir, '../scripts/device/device_data_update.py')

#----------------------------#
# Data gathering and cleanup #
#----------------------------#

# Users
def run_google_user_data_pull():
    print(Fore.RED + "Started: google_user_data_pull.py ...")
    print(Style.RESET_ALL + "google_user_data_pull.py logs:")
    subprocess.run(['python', google_user_data_pull_path])

def run_csv_user_data_merge():
    print(Fore.RED + "Started: csv_user_data_merge.py ...")
    print(Style.RESET_ALL + "csv_user_data_merge.py logs:")
    subprocess.run(['python', csv_user_data_merge_path])

def run_csv_user_data_splitting():
    print(Fore.RED + "Started: csv_user_data_splitting.py ...")
    print(Style.RESET_ALL + "csv_user_data_splitting.py logs:")
    subprocess.run(['python', csv_user_data_splitting_path])

# Devices
def run_google_device_data_pull():
    print(Fore.RED + "Started: google_device_data_pull.py ...")
    print(Style.RESET_ALL + "google_device_data_pull.py logs:")
    subprocess.run(['python', google_device_data_pull_path])

def run_csv_device_data_merge():
    print(Fore.RED + "Started: csv_device_data_merge.py ...")
    print(Style.RESET_ALL + "csv_device_data_merge.py logs:")
    subprocess.run(['python', csv_device_data_merge_path])

#---------------#
# Updating data #
#---------------#
def run_device_data_update():
    print(Fore.RED + "Started: device_data_update.py ...")
    print(Style.RESET_ALL + "device_data_update.py logs:")
    subprocess.run(['python', device_data_update_path])

#----------------#
# Moving of data #
#----------------#
# Moving of users to there correct OU's / If the OU doesn't exist yet they will be created
def run_move_suspended_users():
    print(Fore.RED + "Started: move_suspended_users.py ...")
    print(Style.RESET_ALL + "move_suspended_users.py logs:")
    subprocess.run(['python', move_suspended_users_path])

def run_move_admin_users():
    print(Fore.RED + "Started: move_admin_users.py ...")
    print(Style.RESET_ALL + "move_admin_users.py logs:")
    subprocess.run(['python', move_admin_users_path])

def run_move_users_to_ou():
    print(Fore.RED + "Started: move_users_to_ou.py ...")
    print(Style.RESET_ALL + "move_users_to_ou.py logs:")
    subprocess.run(['python', move_users_to_ou_path])



if __name__ == '__main__':
    # Execute the scripts in the desired order

    #----------------------------#
    # Data gathering and cleanup #
    #----------------------------#
    # Users
    run_google_user_data_pull()
    run_csv_user_data_merge()
    run_csv_user_data_splitting()
    # Devices
    run_google_device_data_pull()
    run_csv_device_data_merge()

    #---------------#
    # Updating data #
    #---------------#

    

    #----------------#
    # Moving of data #
    #----------------#
    # Moving of users to there correct OU's / If the OU doesn't exist yet they will be created
    run_move_suspended_users()
    run_move_admin_users()
    # run_move_users_to_ou()

print(Fore.GREEN + "Full process finished in --- %s seconds ---" % (time.time() - start_time))