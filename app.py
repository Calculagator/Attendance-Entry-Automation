import os
import secrets
from flask import Flask, render_template, request, redirect, url_for, session, flash
from attendance_core import RunOptions, list_sheet_tabs, run_attendance
from dotenv import load_dotenv

# Check for Docker Secret first
if os.path.exists("/run/secrets/app_secret"):
    load_dotenv("/run/secrets/app_secret")
else:
    load_dotenv() # Load variables from local .env file if present

app = Flask(__name__)
# Generate a random secret key for session management, or use the one from environment
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(16))

# Determine credentials path (Docker Secret or Local)
CREDS_PATH = "credentials.json"
if os.path.exists("/run/secrets/g_creds"):
    CREDS_PATH = "/run/secrets/g_creds"

# Load users from environment variables
# In a real app, this would be a database lookup
app_user = os.getenv("FLASK_USERNAME", "admin")
app_pass = os.getenv("FLASK_PASSWORD", "password")

USERS = {
    app_user: app_pass
}

@app.route("/")
def index():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if username in USERS and USERS[username] == password:
            session["logged_in"] = True
            session["username"] = username
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials", "error")
            
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
        
    tabs = []
    # If the user has already entered a URL, try to fetch tabs
    sheet_url = request.args.get("sheet_url", "")
    if sheet_url:
        try:
            tabs = list_sheet_tabs(sheet_url, credentials_path=CREDS_PATH)
        except Exception as e:
            flash(f"Error loading tabs: {str(e)}", "error")

    return render_template("dashboard.html", tabs=tabs, sheet_url=sheet_url)

@app.route("/run_attendance", methods=["POST"])
def perform_attendance():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    try:
        # Extract form data
        attend_type = request.form.get("attend_type")
        sheet_url = request.form.get("sheet_url")
        worksheet_title = request.form.get("worksheet_title")
        row_start_index = int(request.form.get("row_start_index", 1)) - 1
        
        managed_attendance = request.form.get("managed_attendance") == "on"
        validate_name = request.form.get("validate_name") == "on"
        desired_active = int(request.form.get("desired_participants", 0))

        if not sheet_url or not worksheet_title:
            flash("Missing Sheet URL or Worksheet selection.", "error")
            return redirect(url_for("dashboard"))

        # Build Options
        options = RunOptions(
            attend_type=attend_type,
            sheet_url=sheet_url,
            worksheet_title=worksheet_title,
            row_start_index=row_start_index,
            skip_close_to_12=managed_attendance,
            validate_name=validate_name,
            msg_student_ids=[], # TODO: File upload handling if needed later
            desired_participants_to_add=desired_active,
            headless_mode=True
        )
        
        # Run!
        run_attendance(options, credentials_path=CREDS_PATH)
        flash("Attendance Entry Completed Successfully!", "success")
        
    except Exception as e:
        flash(f"Execution Error: {str(e)}", "error")

    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=920)
