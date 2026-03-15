# DevSheriff Demo Target Files

These files are **intentionally vulnerable** Python scripts used to demonstrate DevSheriff's AI-powered code review capabilities.

**DO NOT deploy these files to any real environment.**

| File | Vulnerabilities |
|------|----------------|
| `payment_service.py` | Hardcoded secrets, SQL injection, timing attack, XXE, command injection, SSRF |
| `api_handler.py` | Hardcoded credentials, SQL injection, command injection, MD5 password hashing, insecure deserialization, SSRF, path traversal, ReDoS |
| `auth.py` | Hardcoded secret key, SQL injection, MD5 password hashing, path traversal, command injection, insecure deserialization |

## How to use for demo

1. Copy any of these files into a branch of a repo where DevSheriff is installed
2. Open a pull request
3. DevSheriff will automatically review the diff and post inline comments identifying the vulnerabilities
