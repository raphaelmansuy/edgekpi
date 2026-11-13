resource "google_artifact_registry_repository" "edgekpi" {
  location      = var.region
  repository_id = "edgekpi"
  format        = "DOCKER"
  description   = "Images for the edgekpi demo"

  depends_on = [google_project_service.required]
}

# Cloud Run pulls the image with its own service agent. Same-project access is not always enough for a new repository.
resource "google_artifact_registry_repository_iam_member" "run_reader" {
  location   = google_artifact_registry_repository.edgekpi.location
  repository = google_artifact_registry_repository.edgekpi.repository_id
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:service-${data.google_project.current.number}@serverless-robot-prod.iam.gserviceaccount.com"
}

resource "google_artifact_registry_repository_iam_member" "deploy_writer" {
  location   = google_artifact_registry_repository.edgekpi.location
  repository = google_artifact_registry_repository.edgekpi.repository_id
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.deploy.email}"
}
