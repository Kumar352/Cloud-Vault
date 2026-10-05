output "resources_enabled" {
  description = "False means this configuration intentionally declares no AWS resources."
  value       = var.enable_resources
}

output "quarantine_bucket_name" {
  value       = try(aws_s3_bucket.quarantine[0].bucket, null)
  description = "Available only when resources are explicitly enabled."
}

output "clean_bucket_name" {
  value       = try(aws_s3_bucket.clean[0].bucket, null)
  description = "Available only when resources are explicitly enabled."
}

output "scan_queue_url" {
  value       = try(aws_sqs_queue.scan[0].url, null)
  description = "Available only when resources are explicitly enabled."
}

output "identity_pool_id" {
  value       = try(aws_cognito_user_pool.users[0].id, null)
  description = "Available only when resources and optional identity are explicitly enabled."
}
