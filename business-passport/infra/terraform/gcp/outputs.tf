output "cloud_run_url" {
  value = google_cloud_run_v2_service.inference.uri
}

output "vertex_endpoint_id" {
  value = google_vertex_ai_endpoint.gemma.name
}

output "service_account_email" {
  value       = google_service_account.passport.email
  description = "Store the JSON key for this SA in AWS Secrets Manager as 'gcp-service-account'"
}
