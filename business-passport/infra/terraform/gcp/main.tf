terraform {
  required_providers {
    google = { source = "hashicorp/google", version = "~> 5.0" }
  }
}

provider "google" {
  project = var.gcp_project
  region  = var.gcp_region
}

# ── Service Account ───────────────────────────────────────────────────────────
resource "google_service_account" "passport" {
  account_id   = "passport-inference-sa"
  display_name = "Business Passport Inference SA"
}

resource "google_project_iam_member" "vertex_user" {
  project = var.gcp_project
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.passport.email}"
}

resource "google_project_iam_member" "run_invoker" {
  project = var.gcp_project
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.passport.email}"
}

# ── Cloud Run: inference gateway ──────────────────────────────────────────────
resource "google_cloud_run_v2_service" "inference" {
  name     = "passport-inference-gateway"
  location = var.gcp_region

  template {
    service_account = google_service_account.passport.email

    containers {
      image = var.inference_gateway_image

      resources {
        limits = { cpu = "4", memory = "16Gi" }
        gpu_config { count = 1; type = "nvidia-l4" }
      }

      env { name = "PORT"; value = "8080" }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }
  }
}

# Allow the passport SA to invoke Cloud Run (used by AWS Lambda via bearer token)
resource "google_cloud_run_v2_service_iam_member" "invoker" {
  project  = var.gcp_project
  location = var.gcp_region
  name     = google_cloud_run_v2_service.inference.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.passport.email}"
}

# ── Vertex AI: Gemma 2 endpoint ───────────────────────────────────────────────
# NOTE: Model Garden deployments require manual steps in the GCP Console or gcloud.
# The endpoint resource below registers the endpoint; deploy the model via:
#   gcloud ai endpoints deploy-model <ENDPOINT_ID> --model=google/gemma2@001 ...
resource "google_vertex_ai_endpoint" "gemma" {
  name         = "passport-gemma2-endpoint"
  display_name = "Business Passport Gemma 2"
  location     = var.gcp_region
}

resource "google_vertex_ai_endpoint_iam_member" "sa_user" {
  project  = var.gcp_project
  location = var.gcp_region
  endpoint = google_vertex_ai_endpoint.gemma.name
  role     = "roles/aiplatform.user"
  member   = "serviceAccount:${google_service_account.passport.email}"
}
