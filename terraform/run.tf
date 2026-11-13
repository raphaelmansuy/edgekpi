resource "google_cloud_run_v2_service" "demo" {
  name     = "edgekpi-demo"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  labels = {
    app  = "edgekpi"
    role = "demo"
  }

  # client, client_version, and the top-level scaling block are rewritten by Cloud Run.
  lifecycle {
    ignore_changes = [client, client_version, scaling]
  }

  template {
    labels = {
      app  = "edgekpi"
      role = "demo"
    }

    service_account                  = google_service_account.runtime.email
    timeout                          = "300s"
    max_instance_request_concurrency = 8

    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }

    containers {
      image = var.image

      ports {
        container_port = 8080
        name           = "http1"
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      env {
        name  = "EDGEKPI_MONTHLY_SECONDS"
        value = "86400"
      }

      startup_probe {
        failure_threshold = 1
        period_seconds    = 240
        timeout_seconds   = 240
        tcp_socket {
          port = 8080
        }
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [google_project_service.required, google_project_iam_member.runtime_monitoring]
}

resource "google_cloud_run_v2_service_iam_member" "public" {
  project  = google_cloud_run_v2_service.demo.project
  location = google_cloud_run_v2_service.demo.location
  name     = google_cloud_run_v2_service.demo.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
