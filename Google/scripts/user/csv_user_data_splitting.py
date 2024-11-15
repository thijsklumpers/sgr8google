import csv
import os
import time

start_time = time.time()

# Define the paths based on your file structure
base_dir = os.path.dirname(__file__)
master_csv_path = os.path.join(base_dir, '../../csv/user/merged/merged_user_data.csv')

# Output file paths
suspended_csv_path = os.path.join(base_dir, '../../csv/user/split/split_suspended_google_users.csv')
leerling_csv_path = os.path.join(base_dir, '../../csv/user/split/split_leerling_google_users.csv')
leerkracht_csv_path = os.path.join(base_dir, '../../csv/user/split/split_leerkracht_google_users.csv')
administratie_csv_path = os.path.join(base_dir, '../../csv/user/split/split_administratie_google_users.csv')
non_specific_csv_path = os.path.join(base_dir, '../../csv/user/split/split_google_users.csv')

# Ensure the output directory exists
output_dir = os.path.dirname(suspended_csv_path)
os.makedirs(output_dir, exist_ok=True)

# Open the master CSV file for reading
with open(master_csv_path, mode='r', encoding='utf-8') as master_file:
    reader = csv.DictReader(master_file)
    # Get fieldnames from master file
    fieldnames = reader.fieldnames

    # Open the output CSV files for writing
    with open(suspended_csv_path, mode='w', newline='', encoding='utf-8') as suspended_file, \
         open(leerling_csv_path, mode='w', newline='', encoding='utf-8') as leerling_file, \
         open(leerkracht_csv_path, mode='w', newline='', encoding='utf-8') as leerkracht_file, \
         open(administratie_csv_path, mode='w', newline='', encoding='utf-8') as administratie_file, \
         open(non_specific_csv_path, mode='w', newline='', encoding='utf-8') as non_specific_file:

        # Create CSV writers
        suspended_writer = csv.DictWriter(suspended_file, fieldnames=fieldnames)
        leerling_writer = csv.DictWriter(leerling_file, fieldnames=fieldnames)
        leerkracht_writer = csv.DictWriter(leerkracht_file, fieldnames=fieldnames)
        administratie_writer = csv.DictWriter(administratie_file, fieldnames=fieldnames)
        non_specific_writer = csv.DictWriter(non_specific_file, fieldnames=fieldnames)

        # Write headers to output files
        suspended_writer.writeheader()
        leerling_writer.writeheader()
        leerkracht_writer.writeheader()
        administratie_writer.writeheader()
        non_specific_writer.writeheader()

        # Process each row in the master CSV
        for row in reader:
            suspended_value = row.get('suspended', '').strip().lower()
            job_title = row.get('jobTitle', '').strip()
            if suspended_value == 'true':
                # Write to suspended users file
                suspended_writer.writerow(row)
            else:
                if job_title == 'Leerling':
                    leerling_writer.writerow(row)
                elif job_title in ['Leraar', 'Leraar LBV', 'Leraar LO', 'Zorgcoordinator']:
                    leerkracht_writer.writerow(row)
                elif job_title in ['Directeur', 'Administratief medewerker']:
                    administratie_writer.writerow(row)
                else:
                    non_specific_writer.writerow(row)

print("CSV files have been split successfully.")
print("Process finished --- %s seconds ---" % (time.time() - start_time))