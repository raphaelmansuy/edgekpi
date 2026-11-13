output "service_url" {
  description = "Public URL of the demo."
  value       = google_cloud_run_v2_service.demo.uri
}

output "workload_identity_provider" {
  description = "Provider resource GitHub Actions passes to google-github-actions/auth."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "deploy_service_account" {
  description = "Service account assumed from refs/heads/main."
  value       = google_service_account.deploy.email
}

output "plan_service_account" {
  description = "Read-only service account assumed for terraform plan."
  value       = google_service_account.plan.email
}

output "image_repository" {
  description = "Artifact Registry repository that receives demo images."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.edgekpi.repository_id}/edgekpi-demo"
}
