# DevSheriff

**AI-powered code review and security auditing on every GitHub pull request.**

DevSheriff is a GitHub App that automatically reviews pull requests using Claude AI. It runs two parallel analysis passes — semantic review (bugs, logic, performance) and security audit (OWASP Top 10) — and posts inline comments directly on the PR diff, indistinguishable from a human reviewer.

---

## How It Works

```
Developer pushes to PR
        │
        ▼
GitHub fires signed webhook
        │
        ▼
FastAPI backend (HMAC-SHA256 verified)
        │
        ▼
GitHub App auth: JWT → Installation Token
        │
        ▼
Fetch PR files + unified diffs
        │
        ├─────────────────────┐
        ▼                     ▼
Semantic pass (Claude)   Security pass (Claude)
Bugs, logic, perf        OWASP Top 10, secrets
        │                     │
        └──────────┬──────────┘
                   ▼
        Map findings → diff line positions
                   │
                   ▼
        Post inline review comments on PR
        Set commit status (pass / fail)
        Save audit log → Firestore
```

---

## Project Structure

```
devsheriff/
├── backend/                          # FastAPI backend
│   ├── app/
│   │   ├── main.py                   # FastAPI app, webhook router
│   │   ├── config/
│   │   │   ├── __init__.py           # Settings (pydantic-settings), secret loading
│   │   │   └── repo_config.py        # Per-repo .devsheriff.yml config loader
│   │   ├── middleware/
│   │   │   └── signature_middleware.py  # HMAC-SHA256 webhook verification
│   │   ├── models/
│   │   │   └── github_events.py      # Pydantic models for GitHub webhook payloads
│   │   ├── services/
│   │   │   ├── auth_service.py       # GitHub App JWT → installation token
│   │   │   ├── github_service.py     # PR fetch, review posting, commit status
│   │   │   ├── review_engine.py      # Two-pass Claude AI review pipeline
│   │   │   ├── diff_parser.py        # Unified diff → line position mapping
│   │   │   ├── dependency_scanner.py # pip-audit + OSV vulnerability scanning
│   │   │   ├── firestore_service.py  # Audit log read/write
│   │   │   ├── nvd_service.py        # NVD CVE enrichment
│   │   │   └── osv_service.py        # OSV database integration
│   │   └── utils/
│   │       └── logger.py             # Structured JSON logger
│   ├── requirements.txt
│   └── .env.example
├── dashboard/                        # React + TypeScript frontend
│   ├── src/
│   │   ├── components/               # UI components (shadcn/ui)
│   │   ├── hooks/                    # Firestore real-time hooks
│   │   └── pages/                    # Reviews list, review detail
│   ├── package.json
│   └── vite.config.ts
├── demo/                             # Intentionally vulnerable files for demo
│   ├── payment_service.py            # 6 vulnerabilities (SQL injection, SSRF, etc.)
│   ├── api_handler.py                # 7 vulnerabilities
│   ├── auth.py                       # 5 vulnerabilities
│   └── README.md
├── terraform/                        # GCP infrastructure (Cloud Run, Firestore, etc.)
├── cloudbuild.yaml                   # Cloud Build CI/CD pipeline
├── DEMO_SCRIPT.md                    # Live and recorded demo scripts
└── DEVPOST.md                        # DevPost submission write-up
```

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- A GitHub App (see below)
- An Anthropic API key with credits
- `smee` CLI for local webhook tunneling: `npm install -g smee-client`

### 1. Create a GitHub App

Go to **GitHub Settings → Developer settings → GitHub Apps → New GitHub App**.

Configure:
- **Webhook URL**: your smee.io proxy URL (local dev) or Cloud Run URL (prod)
- **Webhook secret**: generate a random string, save it
- **Repository permissions**:
  - Contents: Read
  - Pull requests: Read & Write
  - Commit statuses: Read & Write
- **Subscribe to events**: Pull requests, Check suites
- **Generate a private key** and download the `.pem` file

Install the app on the target repository.

### 2. Clone and configure

```bash
git clone https://github.com/AlhichriMaster/DevSheriff.git
cd DevSheriff/backend
cp .env.example .env
```

Edit `.env`:

```env
GITHUB_APP_ID=<your app ID>
GITHUB_PRIVATE_KEY_PATH=./your-app.pem
GITHUB_WEBHOOK_SECRET=<your webhook secret>
ANTHROPIC_API_KEY=sk-ant-...
ENVIRONMENT=development

# Optional
FIRESTORE_PROJECT_ID=your-gcp-project
NVD_API_KEY=your-nvd-key
```

### 3. Install backend dependencies

```bash
cd backend
python -m venv .venv
# Windows:
.venv/Scripts/activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 4. Install dashboard dependencies

```bash
cd dashboard
npm install
```

### 5. Start local development

**Terminal 1 — Backend:**
```bash
cd backend
.venv/Scripts/python -m uvicorn app.main:app --port 8080 --reload
```

**Terminal 2 — Webhook tunnel:**
```bash
smee --url https://smee.io/YOUR_CHANNEL --target http://localhost:8080/webhook
```

**Terminal 3 — Dashboard (optional):**
```bash
cd dashboard
npm run dev
```

Open a pull request on the repo where you installed the GitHub App — DevSheriff will review it automatically.

---

## Per-Repository Configuration

DevSheriff reads an optional `.devsheriff.yml` from the repository root:

```yaml
review:
  enabled: true
  ignore_paths:
    - "*.lock"
    - "dist/**"
    - "*.min.js"
  max_files_per_pr: 20

security:
  enabled: true
  scan_dependencies: true
  block_merge_on:
    - critical
    - high
```

If no config file is present, sensible defaults are used.

---

## What DevSheriff Catches

### Semantic Pass
- Logic errors and off-by-one bugs
- Performance anti-patterns (N+1 queries, unnecessary recomputation, blocking I/O in async context)
- Missing error handling and unhandled edge cases
- Poor naming and readability issues
- Maintainability concerns (functions too long, magic numbers, missing docstrings)

### Security Pass (OWASP Top 10)
- SQL, command, LDAP, XPath injection (A03)
- Hardcoded secrets, API keys, passwords (A02)
- Insecure cryptography — MD5/SHA1 for passwords, ECB mode (A02)
- Path traversal and file inclusion (A01)
- Insecure deserialization (A08)
- Missing authentication or authorization (A07)
- SSRF and open redirects (A10)
- XSS vectors (A03)
- Regex denial of service — ReDoS (A06)
- XXE injection (A05)

### Dependency Scanning
- Known CVEs in Python dependencies via pip-audit and the OSV database
- NVD enrichment for CVSS scores

---

## Deploying to Production (GCP)

```bash
# Build and push container
gcloud builds submit --config cloudbuild.yaml

# Apply infrastructure
cd terraform
terraform init
terraform apply
```

Set environment variables in Cloud Run:
- `ENVIRONMENT=production`
- `GCP_PROJECT_ID=your-project`

In production, secrets are loaded from Google Secret Manager automatically.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, uvicorn |
| AI | Claude Sonnet 4.6 (Anthropic API) |
| GitHub integration | PyGithub, PyJWT (RS256) |
| HTTP client | httpx (async) |
| Frontend | React 18, TypeScript, Vite, TailwindCSS, shadcn/ui |
| Database | Google Cloud Firestore |
| Hosting | Google Cloud Run |
| Secrets | Google Secret Manager |
| CI/CD | Google Cloud Build |
| Infrastructure | Terraform |
| Dev tunneling | smee.io |
