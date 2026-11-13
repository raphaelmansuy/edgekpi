resource "google_service_account" "runtime" {
  account_id   = "edgekpi-demo-runtime"
  display_name = "edgekpi demo runtime"
  description  = "Identity of the Cloud Run demo. Reads Cloud Monitoring for the monthly time cap."
}

resource "google_service_account" "deploy" {
  account_id   = "edgekpi-demo-deploy"
  display_name = "edgekpi demo deploy"
  description  = "GitHub Actions on main. Applies this module and pushes images."
}

resource "google_service_account" "plan" {
  account_id   = "edgekpi-demo-plan"
  display_name = "edgekpi demo plan"
  description  = "GitHub Actions on pull requests. Reads infrastructure so it can plan. Cannot apply."
}

resource "google_project_iam_member" "runtime_monitoring" {
  project = var.project_id
  role    = "roles/monitoring.viewer"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

# run.admin, not run.developer: this module also manages the public invoker binding, and developer cannot read or set that policy.
resource "google_project_iam_member" "deploy_run" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.deploy.email}"
}

# Read IAM policies and workload identity during refresh. Apply still cannot grant project roles it does not hold.
resource "google_project_iam_member" "deploy_read" {
  for_each = toset([
    "roles/iam.securityReviewer",
    "roles/iam.serviceAccountViewer",
    "roles/iam.workloadIdentityPoolViewer",
    "roles/serviceusage.serviceUsageViewer",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.deploy.email}"
}

resource "google_project_iam_member" "plan_read" {
  for_each = toset([
    "roles/viewer",
    "roles/iam.securityReviewer",
    "roles/iam.serviceAccountViewer",
    "roles/iam.workloadIdentityPoolViewer",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.plan.email}"
}

resource "google_service_account_iam_member" "deploy_acts_as_runtime" {
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deploy.email}"
}

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "edgekpi-github"
  display_name              = "edgekpi GitHub"
  description               = "GitHub Actions for ${var.github_repository}."

  depends_on = [google_project_service.required]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github"
  display_name                       = "GitHub"
  description                        = "Tokens from ${var.github_repository} on main or a pull request."

  attribute_condition = <<-EOT
    assertion.repository == "${var.github_repository}" && (
      assertion.ref == "refs/heads/main" ||
      assertion.ref.startsWith("refs/pull/")
    )
  EOT

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# This repository was created after GitHub switched new repositories to immutable
# subject claims, so the subject carries the owner and repository ids.
# Confirmed from the repository OIDC settings: raphaelmansuy@1003084/edgekpi@1455979235.
resource "google_service_account_iam_member" "deploy_wif" {
  service_account_id = google_service_account.deploy.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principal://iam.googleapis.com/projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${google_iam_workload_identity_pool.github.workload_identity_pool_id}/subject/repo:raphaelmansuy@1003084/edgekpi@1455979235:ref:refs/heads/main"
}

resource "google_service_account_iam_member" "plan_wif" {
  service_account_id = google_service_account.plan.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${google_iam_workload_identity_pool.github.workload_identity_pool_id}/attribute.repository/${var.github_repository}"
}
