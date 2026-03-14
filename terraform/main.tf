terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  backend "gcs" {
    bucket = "devsheriff-tfstate"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "firestore.googleapis.com",
    "secretmanager.googleapis.com",
    "logging.googleapis.com",
  ])
  service            = each.key
  disable_on_destroy = false
}

# Artifact Registry for Docker images
resource "google_artifact_registry_repository" "images" {
  location      = var.region
  repository_id = "devsheriff-images"
  format        = "DOCKER"
  description   = "DevSheriff Docker images"

  depends_on = [google_project_service.apis]
}

# Firestore database
resource "google_firestore_database" "default" {
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.apis]
}

# Service account for Cloud Run
resource "google_service_account" "runner" {
  account_id   = "devsheriff-runner"
  display_name = "DevSheriff Cloud Run SA"
}

# IAM bindings for the service account
resource "google_project_iam_member" "firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.runner.email}"
}

resource "google_project_iam_member" "secret_access" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.runner.email}"
}

resource "google_project_iam_member" "log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.runner.email}"
}

# Secrets (values must be set separately via gcloud CLI)
resource "google_secret_manager_secret" "github_private_key" {
  secret_id = "devsheriff-github-private-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "webhook_secret" {
  secret_id = "devsheriff-github-webhook-secret"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "anthropic_api_key" {
  secret_id = "devsheriff-anthropic-api-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "nvd_api_key" {
  secret_id = "devsheriff-nvd-api-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

# Cloud Run — Backend
resource "google_cloud_run_v2_service" "backend" {
  name     = "devsheriff-backend"
  location = var.region

  template {
    service_account = google_service_account.runner.email
    timeout         = "120s"

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/devsheriff-images/backend:latest"

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          memory = "1Gi"
          cpu    = "1"
        }
      }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }

      env {
        name  = "FIRESTORE_PROJECT_ID"
        value = var.project_id
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
    }
  }

  depends_on = [google_project_service.apis]
}

# Cloud Run — Dashboard
resource "google_cloud_run_v2_service" "dashboard" {
  name     = "devsheriff-dashboard"
  location = var.region

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/devsheriff-images/dashboard:latest"

      ports {
        container_port = 80
      }

      resources {
        limits = {
          memory = "256Mi"
          cpu    = "0.5"
        }
      }
    }
  }

  depends_on = [google_project_service.apis]
}

# Allow unauthenticated access to both services
resource "google_cloud_run_service_iam_member" "backend_public" {
  location = google_cloud_run_v2_service.backend.location
  project  = var.project_id
  service  = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_service_iam_member" "dashboard_public" {
  location = google_cloud_run_v2_service.dashboard.location
  project  = var.project_id
  service  = google_cloud_run_v2_service.dashboard.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
