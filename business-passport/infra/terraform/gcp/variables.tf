variable "gcp_project"              { description = "GCP project ID" }
variable "gcp_region"               { default = "us-central1" }
variable "inference_gateway_image"  { description = "Cloud Run container image URI (e.g. gcr.io/PROJECT/passport-inference:latest)" }
