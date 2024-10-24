import os
import time
import pandas as pd
from config_device import base_dir

start_time = time.time()

# Load device data from Google
exported_device_data_file = os.path.join(base_dir, '../../csv/device/core/all_google_device_data.csv')
device_data = pd.read_csv(exported_device_data_file)

# Load data from provider
provider_data_file = os.path.join(base_dir, '../../csv/device/Export_hardware.csv')
provider_data = pd.read_csv(provider_data_file, delimiter=';')

# Standardize column names
device_data.rename(columns={'serialNumber': 'Serial Number'}, inplace=True)
provider_data.rename(columns={'serienummer': 'Serial Number'}, inplace=True)

# Merge the two datasets on the Serial Number column
merged_data = pd.merge(device_data, provider_data, on='Serial Number', how='outer', indicator=True)

# Separate the merged data into different categories
# Rows that exist in both files (matching data)
matching_devices = merged_data[merged_data['_merge'] == 'both']

# Rows that are only in one of the files (error logs)
error_devices = merged_data[merged_data['_merge'] != 'both']

# Save results to CSV files
matching_devices.to_csv(os.path.join(base_dir, '../../csv/device/matching_devices.csv'), index=False)

# Write error logs
with open(os.path.join(base_dir, '../../logs/google_device_error_logs.csv'), 'w') as error_log:
    error_log.write('Serial Number,Issue Found In File\n')
    for _, row in error_devices.iterrows():
        if row['_merge'] == 'left_only':
            error_log.write(f"{row['Serial Number']},all_google_device_data.csv\n")
        elif row['_merge'] == 'right_only':
            error_log.write(f"{row['Serial Number']},Export_hardware.csv\n")

print("Matching devices saved to 'matching_devices.csv'")
print("Error logs saved to 'google_device_error_logs.csv'")
print("Process finished in --- %s seconds ---" % (time.time() - start_time))