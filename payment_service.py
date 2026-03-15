"""
Payment service — intentionally vulnerable for DevSheriff demo.
"""

import hashlib
import sqlite3
import subprocess
import xml.etree.ElementTree as ET

# VULNERABILITY: Hardcoded payment processor credentials
STRIPE_SECRET_KEY = "sk_live_abc123def456ghi789"
PAYPAL_CLIENT_SECRET = "EBWKjlELKMYqRNQ6sYvFo64FtaoneI-1"

def process_payment(user_id, amount, card_number):
    # VULNERABILITY: Logging sensitive data
    print(f"Processing payment for user={user_id} card={card_number} amount={amount}")

    # VULNERABILITY: SQL injection
    conn = sqlite3.connect("payments.db")
    conn.execute(f"INSERT INTO transactions VALUES ('{user_id}', {amount}, '{card_number}')")

def verify_webhook(payload, signature):
    # VULNERABILITY: Timing attack on signature comparison
    expected = hashlib.sha256(payload.encode()).hexdigest()
    return signature == expected  # should use hmac.compare_digest

def parse_payment_xml(xml_data):
    # VULNERABILITY: XXE injection — external entity expansion enabled
    tree = ET.fromstring(xml_data)
    return tree.find("amount").text

def generate_receipt(order_id):
    # VULNERABILITY: Command injection
    subprocess.call(f"generate_receipt.sh {order_id}", shell=True)

def get_exchange_rate(currency):
    # VULNERABILITY: SSRF via user-controlled currency code
    import urllib.request
    url = f"http://internal-rates-api/{currency}"
    return urllib.request.urlopen(url).read()
