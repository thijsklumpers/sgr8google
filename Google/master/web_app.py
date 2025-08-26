import subprocess
import os
from flask import Flask, render_template, Response

app = Flask(__name__)

# Get the current working directory dynamically
base_dir = os.path.dirname(os.path.abspath(__file__))

# --- Script Paths ---
scripts = {
    "Pull Google User Data": os.path.join(base_dir, '../scripts/user/google_user_data_pull.py'),
    "Merge CSV User Data": os.path.join(base_dir, '../scripts/user/csv_user_data_merge.py'),
    "Split CSV User Data": os.path.join(base_dir, '../scripts/user/csv_user_data_splitting.py'),
    "Pull Google Device Data": os.path.join(base_dir, '../scripts/device/google_device_data_pull.py'),
    "Merge CSV Device Data": os.path.join(base_dir, '../scripts/device/csv_device_data_merge.py'),
    "Update Device Data": os.path.join(base_dir, '../scripts/device/device_data_update.py'),
    "Move Suspended Users": os.path.join(base_dir, '../scripts/user/move_suspended_users.py'),
    "Move Admin Users": os.path.join(base_dir, '../scripts/user/move_admin_users.py'),
    "Move Users to OU": os.path.join(base_dir, '../scripts/user/move_users_to_ou.py'),
}

@app.route('/')
def index():
    return render_template('index.html', scripts=scripts.keys())

@app.route('/run_script/<script_name>')
def run_script(script_name):
    script_path = scripts.get(script_name)
    if not script_path:
        return Response(f"Script '{script_name}' not found.", mimetype='text/plain')

    def generate_output():
        yield f"--- Running {os.path.basename(script_path)} ---" + "\n"
        process = subprocess.Popen(['python', script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)

        for line in iter(process.stdout.readline, ''):
            yield line
        
        process.stdout.close()
        return_code = process.wait()
        yield f"\n--- Finished {os.path.basename(script_path)} with exit code {return_code} ---" + "\n"

    return Response(generate_output(), mimetype='text/plain')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)