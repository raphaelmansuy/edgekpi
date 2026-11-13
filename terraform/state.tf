resource "google_storage_bucket" "tfstate" {
  name                        = "${var.project_id}-edgekpi-tfstate"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  versioning {
    enabled = true
  }

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_project_service.required]
}

resource "google_storage_bucket_iam_member" "state" {
  for_each = {
    deploy = google_service_account.deploy.email
    plan   = google_service_account.plan.email
  }

  bucket = google_storage_bucket.tfstate.name
  role   = "roles/storage.admin"
  member = "serviceAccount:${each.value}"
}
