variable "project_id" {
  description = "GCP project that hosts the demo. This module does not manage the rest of the project."
  type        = string
  default     = "saas-app-001"
}

variable "region" {
  description = "Region for Cloud Run and Artifact Registry. us-central1 is a Cloud Run Tier 1 region."
  type        = string
  default     = "us-central1"
}

variable "github_repository" {
  description = "GitHub repository allowed to assume the deploy and plan identities."
  type        = string
  default     = "raphaelmansuy/edgekpi"
}

variable "image" {
  description = "Container image Cloud Run serves. CI passes the image it just built; a plan passes the image already deployed."
  type        = string
}
