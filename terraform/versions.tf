terraform {
  required_version = ">= 1.10"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  backend "gcs" {
    bucket = "saas-app-001-edgekpi-tfstate"
    prefix = "edgekpi"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
