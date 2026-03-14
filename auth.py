"""
Demo file — intentionally vulnerable code for DevSheriff demonstration.
DO NOT deploy to production.
"""

import sqlite3
import hashlib
import os


# VULNERABILITY: Hardcoded secret key
SECRET_KEY = "super_secret_key_12345"


def login(username, password):
    # VULNERABILITY: SQL injection via f-string interpolation
    conn = sqlite3.connect("users.db")
    cursor = conn.execute(f"SELECT * FROM users WHERE username = '{username}'")
    user = cursor.fetchone()

    if user is None:
        return False

    # VULNERABILITY: MD5 for password hashing (broken cryptography)
    stored_hash = user[2]
    if hashlib.md5(password.encode()).hexdigest() == stored_hash:
        return True
    return False


def get_file(path):
    # VULNERABILITY: Path traversal — no sanitization of user-supplied path
    base = "/var/app/files/"
    return open(base + path).read()


def run_report(report_name):
    # VULNERABILITY: OS command injection via unsanitized input
    os.system(f"generate_report.sh {report_name}")


def deserialize_data(data):
    # VULNERABILITY: Insecure deserialization
    import pickle
    return pickle.loads(data)
