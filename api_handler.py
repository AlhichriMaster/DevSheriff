"""
API handler — intentionally vulnerable for DevSheriff demo.
"""

import os
import subprocess
import hashlib
import pickle
import requests

# VULNERABILITY: Hardcoded credentials
DB_PASSWORD = "admin123"
API_SECRET = "sk-prod-abc123xyz"

def get_user_data(user_id):
    # VULNERABILITY: SQL injection via f-string
    import sqlite3
    conn = sqlite3.connect("app.db")
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return conn.execute(query).fetchall()

def run_command(filename):
    # VULNERABILITY: OS command injection
    result = subprocess.run(f"process_file.sh {filename}", shell=True, capture_output=True)
    return result.stdout

def hash_password(password):
    # VULNERABILITY: MD5 for password hashing
    return hashlib.md5(password.encode()).hexdigest()

def load_user_session(session_data):
    # VULNERABILITY: Insecure deserialization
    return pickle.loads(session_data)

def fetch_url(user_supplied_url):
    # VULNERABILITY: SSRF — no URL validation
    return requests.get(user_supplied_url).text

def read_file(filename):
    # VULNERABILITY: Path traversal
    base_dir = "/var/app/uploads/"
    with open(base_dir + filename) as f:
        return f.read()

def validate_email(email):
    import re
    # VULNERABILITY: ReDoS — catastrophic backtracking
    pattern = r"^([a-zA-Z0-9]+(\.)?)*@([a-zA-Z0-9]+(\.)?)*\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None
