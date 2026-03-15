# DevSheriff — Production Deployment Guide

This guide deploys DevSheriff fully to Google Cloud Platform so nothing runs locally.
After completing these steps: the backend runs on Cloud Run, the dashboard is on Cloud Run,
and the GitHub App webhook points directly to your public Cloud Run URL.

**GCP Project ID:** `alhichdevsheriff`
**Region:** `us-central1`

---

## Prerequisites

```bash
# Install Google Cloud CLI if not already installed
# https://cloud.google.com/sdk/docs/install

gcloud auth login
gcloud config set project alhichdevsheriff
```

---

## Step 1 — Enable GCP APIs

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  firestore.googleapis.com
```

---

## Step 2 — Create Artifact Registry repository

```bash
gcloud artifacts repositories create devsheriff-images \
  --repository-format=docker \
  --location=us-central1 \
  --description="DevSheriff container images"
```

---

## Step 3 — Create service account and grant permissions

```bash
# Create the service account that Cloud Run will run as
gcloud iam service-accounts create devsheriff-runner \
  --display-name="DevSheriff Cloud Run Runner"

# Allow it to read secrets from Secret Manager
gcloud projects add-iam-policy-binding alhichdevsheriff \
  --member="serviceAccount:devsheriff-runner@alhichdevsheriff.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Allow it to read/write Firestore
gcloud projects add-iam-policy-binding alhichdevsheriff \
  --member="serviceAccount:devsheriff-runner@alhichdevsheriff.iam.gserviceaccount.com" \
  --role="roles/datastore.user"
```

---

## Step 4 — Store secrets in Secret Manager

```bash
# GitHub App private key
gcloud secrets create devsheriff-github-private-key \
  --data-file=backend/alhichdevsheriff.2026-03-14.private-key.pem

# GitHub webhook secret (the value you set in the GitHub App settings)
echo -n "YOUR_WEBHOOK_SECRET_HERE" | \
  gcloud secrets create devsheriff-github-webhook-secret --data-file=-

# Anthropic API key
echo -n "sk-ant-api03-YOUR_KEY_HERE" | \
  gcloud secrets create devsheriff-anthropic-api-key --data-file=-

# NVD API key (get free key at https://nvd.nist.gov/developers/request-an-api-key)
echo -n "YOUR_NVD_KEY_HERE" | \
  gcloud secrets create devsheriff-nvd-api-key --data-file=-
```

---

## Step 5 — Grant Cloud Build permissions

```bash
PROJECT_NUMBER=$(gcloud projects describe alhichdevsheriff --format='value(projectNumber)')
CB_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

gcloud projects add-iam-policy-binding alhichdevsheriff \
  --member="serviceAccount:${CB_SA}" --role="roles/run.admin"

gcloud projects add-iam-policy-binding alhichdevsheriff \
  --member="serviceAccount:${CB_SA}" --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding alhichdevsheriff \
  --member="serviceAccount:${CB_SA}" --role="roles/artifactregistry.admin"
```

---

## Step 6 — Initialize Firestore

```bash
# Create Firestore database in native mode
gcloud firestore databases create --location=us-central1
```

---

## Step 7 — Deploy

```bash
# From the repo root (devsheriff/)
gcloud builds submit --config cloudbuild.yaml --project=alhichdevsheriff
```

This runs the full pipeline:
1. Runs tests
2. Builds backend Docker image → pushes to Artifact Registry → deploys to Cloud Run
3. Builds dashboard Docker image (React + Nginx) → pushes → deploys to Cloud Run

Takes ~5-10 minutes. Watch progress at:
https://console.cloud.google.com/cloud-build/builds?project=alhichdevsheriff

---

## Step 8 — Get your public URLs

```bash
# Backend URL (this is your webhook URL)
gcloud run services describe devsheriff-backend \
  --region=us-central1 --format='value(status.url)'

# Dashboard URL
gcloud run services describe devsheriff-dashboard \
  --region=us-central1 --format='value(status.url)'
```

---

## Step 9 — Update GitHub App webhook URL

1. Go to **github.com/settings/apps** → your DevSheriff app → **General**
2. Change **Webhook URL** from `https://smee.io/...` to your Cloud Run backend URL + `/webhook`
   - Example: `https://devsheriff-backend-abc123-uc.a.run.app/webhook`
3. Save changes

---

## Step 10 — Update CORS for dashboard

Edit [backend/app/main.py](backend/app/main.py) and add your dashboard Cloud Run URL to `_ALLOWED_ORIGINS`:

```python
_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://devsheriff.run.app",
    "https://YOUR-DASHBOARD-URL.a.run.app",  # add this
]
```

Then redeploy:
```bash
gcloud builds submit --config cloudbuild.yaml --project=alhichdevsheriff
```

---

## Verification

```bash
# Health check
curl https://YOUR-BACKEND-URL.a.run.app/health
# Expected: {"status": "ok", "service": "devsheriff-backend"}
```

Open a pull request on any repo where DevSheriff is installed — it will automatically
review the PR without any local processes running.

---

## Cost estimate (GCP free tier friendly)

| Service | Usage | Cost |
|---------|-------|------|
| Cloud Run backend | ~0 requests at rest (min-instances=1 for always-on) | ~$5-10/mo |
| Cloud Run dashboard | Nginx serving static files | ~$0-2/mo |
| Firestore | Read/writes per review | ~$0-1/mo |
| Artifact Registry | Container storage | ~$0-1/mo |
| Secret Manager | 4 secrets | ~$0/mo (free tier) |
| **Total** | | **~$5-15/mo** |

Set `--min-instances=0` on the backend to scale to zero (free when idle, ~3s cold start).
