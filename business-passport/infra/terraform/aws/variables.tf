variable "aws_region"         { default = "us-east-1" }
variable "s3_bucket_name"     { default = "business-passport-jobs" }
variable "dynamodb_table"     { default = "business-passport-jobs" }
variable "gcp_sa_secret_name" { default = "gcp-service-account" }
variable "cloud_run_url"      { description = "GCP Cloud Run inference gateway URL" }
variable "vertex_project"     { description = "GCP project ID" }
variable "vertex_region"      { default = "us-central1" }
variable "vertex_endpoint_id" { description = "Vertex AI endpoint ID for Gemma 2" }
