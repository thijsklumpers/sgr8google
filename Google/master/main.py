import subprocess
import os
import time
import tkinter as tk
from tkinter import ttk, scrolledtext
import webbrowser

# Get the current working directory dynamically
base_dir = os.path.dirname(os.path.abspath(__file__))

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

def run_script(script_path, output_widget):
    output_widget.insert(tk.END, f"--- Running {os.path.basename(script_path)} ---\n")
    output_widget.see(tk.END)
    process = subprocess.Popen(['python', script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags=subprocess.CREATE_NO_WINDOW) 
    
    for line in iter(process.stdout.readline, ''):
        output_widget.insert(tk.END, line)
        # Check for file paths and make them clickable
        if "file://" in line:
            start_index = line.find("file://")
            end_index = len(line)
            path = line[start_index:].strip()
            make_clickable(output_widget, path)
        output_widget.see(tk.END)
    
    process.stdout.close()
    return_code = process.wait()
    output_widget.insert(tk.END, f"--- Finished {os.path.basename(script_path)} with exit code {return_code}---\n")
    output_widget.see(tk.END)

def make_clickable(widget, path):
    tag_name = f"link-{path}"
    widget.tag_configure(tag_name, foreground="blue", underline=True)
    widget.tag_bind(tag_name, "<Button-1>", lambda e, p=path: webbrowser.open(p))
    
    # Apply the tag to the path
    start_index = widget.search(path, "1.0", tk.END)
    end_index = f"{start_index}+{len(path)}c"
    widget.tag_add(tag_name, start_index, end_index)

def create_gui():
    root = tk.Tk()
    root.title("Google Workspace Control Panel")

    main_frame = ttk.Frame(root, padding="10")
    main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    # --- Buttons ---
    button_frame = ttk.LabelFrame(main_frame, text="Actions")
    button_frame.grid(row=0, column=0, padx=5, pady=5, sticky=(tk.N, tk.S))

    scripts = {
        "Pull Google User Data": google_user_data_pull_path,
        "Merge CSV User Data": csv_user_data_merge_path,
        "Split CSV User Data": csv_user_data_splitting_path,
        "Pull Google Device Data": google_device_data_pull_path,
        "Merge CSV Device Data": csv_device_data_merge_path,
        "Update Device Data": device_data_update_path,
        "Move Suspended Users": move_suspended_users_path,
        "Move Admin Users": move_admin_users_path,
        "Move Users to OU": move_users_to_ou_path,
    }

    row = 0
    for name, path in scripts.items():
        button = ttk.Button(button_frame, text=name, command=lambda p=path: run_script(p, output_text))
        button.grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        row += 1

    # --- Output ---
    output_frame = ttk.LabelFrame(main_frame, text="Output")
    output_frame.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, width=80, height=25)
    output_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    main_frame.columnconfigure(1, weight=1)

    root.mainloop()

if __name__ == '__main__':
    create_gui()