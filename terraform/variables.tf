variable "project_id" {
  description = "GCP project ID"
  type        = string
  default     = "devsheriff-prod"
}

variable "region" {
  description = "GCP region for all resources"
  type        = string
  default     = "us-central1"
}
