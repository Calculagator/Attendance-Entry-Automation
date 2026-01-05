import os
import sys
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Import app to check configuration
# This will run the module-level code in app.py
try:
    from app import app
except Exception as e:
    print(f"Error importing app: {e}")
    sys.exit(1)

env_key = os.getenv("SECRET_KEY")
app_key = app.secret_key

print(f"Environment SECRET_KEY present: {bool(env_key)}")
print(f"App secret_key set: {bool(app_key)}")

if env_key and app_key == env_key:
    print("SUCCESS: App is using SECRET_KEY from environment.")
else:
    print(f"FAILURE: Key mismatch or missing. Env: {bool(env_key)}, App: {bool(app_key)}")
    if app_key and not env_key:
        print("App is using a generated key (fallback active).")
