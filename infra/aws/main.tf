resource "random_id" "suffix" {
  count       = var.enable_resources ? 1 : 0
  byte_length = 3
}

locals {
  suffix = var.enable_resources ? random_id.suffix[0].hex : "disabled"
  common_tags = {
    DataClass  = "synthetic-demo-only"
    CostCenter = "portfolio"
  }
}

resource "aws_s3_bucket" "quarantine" {
  count         = var.enable_resources ? 1 : 0
  bucket        = "${var.name_prefix}-quarantine-${local.suffix}"
  force_destroy = false
  tags          = merge(local.common_tags, { Purpose = "untrusted-quarantine" })
}

resource "aws_s3_bucket" "clean" {
  count         = var.enable_resources ? 1 : 0
  bucket        = "${var.name_prefix}-clean-${local.suffix}"
  force_destroy = false
  tags          = merge(local.common_tags, { Purpose = "scanner-approved-objects" })
}

resource "aws_s3_bucket_public_access_block" "quarantine" {
  count                   = var.enable_resources ? 1 : 0
  bucket                  = aws_s3_bucket.quarantine[0].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "clean" {
  count                   = var.enable_resources ? 1 : 0
  bucket                  = aws_s3_bucket.clean[0].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "quarantine" {
  count  = var.enable_resources ? 1 : 0
  bucket = aws_s3_bucket.quarantine[0].id
  rule { object_ownership = "BucketOwnerEnforced" }
}

resource "aws_s3_bucket_ownership_controls" "clean" {
  count  = var.enable_resources ? 1 : 0
  bucket = aws_s3_bucket.clean[0].id
  rule { object_ownership = "BucketOwnerEnforced" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "quarantine" {
  count  = var.enable_resources ? 1 : 0
  bucket = aws_s3_bucket.quarantine[0].id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "clean" {
  count  = var.enable_resources ? 1 : 0
  bucket = aws_s3_bucket.clean[0].id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "quarantine" {
  count  = var.enable_resources ? 1 : 0
  bucket = aws_s3_bucket.quarantine[0].id
  rule {
    id     = "expire-demo-quarantine"
    status = "Enabled"
    filter {}
    expiration { days = var.retention_days }
    abort_incomplete_multipart_upload { days_after_initiation = 1 }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "clean" {
  count  = var.enable_resources ? 1 : 0
  bucket = aws_s3_bucket.clean[0].id
  rule {
    id     = "expire-demo-clean-objects"
    status = "Enabled"
    filter {}
    expiration { days = var.retention_days }
    abort_incomplete_multipart_upload { days_after_initiation = 1 }
  }
}

resource "aws_s3_bucket_policy" "quarantine_tls_only" {
  count  = var.enable_resources ? 1 : 0
  bucket = aws_s3_bucket.quarantine[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport"
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource  = [aws_s3_bucket.quarantine[0].arn, "${aws_s3_bucket.quarantine[0].arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
  depends_on = [aws_s3_bucket_public_access_block.quarantine]
}

resource "aws_s3_bucket_policy" "clean_tls_only" {
  count  = var.enable_resources ? 1 : 0
  bucket = aws_s3_bucket.clean[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport"
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource  = [aws_s3_bucket.clean[0].arn, "${aws_s3_bucket.clean[0].arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
  depends_on = [aws_s3_bucket_public_access_block.clean]
}

resource "aws_sqs_queue" "scan_dlq" {
  count                      = var.enable_resources ? 1 : 0
  name                       = "${var.name_prefix}-scan-dlq-${local.suffix}"
  message_retention_seconds  = 1209600
  sqs_managed_sse_enabled    = true
  visibility_timeout_seconds = 900
  tags                       = merge(local.common_tags, { Purpose = "scan-dead-letter" })
}

resource "aws_sqs_queue" "scan" {
  count                      = var.enable_resources ? 1 : 0
  name                       = "${var.name_prefix}-scan-${local.suffix}"
  message_retention_seconds  = 86400
  sqs_managed_sse_enabled    = true
  visibility_timeout_seconds = 900
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.scan_dlq[0].arn
    maxReceiveCount     = 2
  })
  tags = merge(local.common_tags, { Purpose = "file-scan-work-queue" })
}

resource "aws_cloudwatch_log_group" "api" {
  count             = var.enable_resources ? 1 : 0
  name              = "/cloudvault/reference/api"
  retention_in_days = var.retention_days
  tags              = merge(local.common_tags, { Purpose = "metadata-only-application-logs" })
}

resource "aws_cognito_user_pool" "users" {
  count = var.enable_resources && var.enable_identity ? 1 : 0
  name  = "${var.name_prefix}-users"
  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = true
    require_uppercase                = true
    temporary_password_validity_days = 1
  }
  auto_verified_attributes = ["email"]
  tags                     = merge(local.common_tags, { Purpose = "identity-reference" })
}

resource "aws_cognito_user_pool_client" "web" {
  count                                = var.enable_resources && var.enable_identity ? 1 : 0
  name                                 = "${var.name_prefix}-web"
  user_pool_id                         = aws_cognito_user_pool.users[0].id
  generate_secret                      = false
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  supported_identity_providers         = ["COGNITO"]
  callback_urls                        = ["http://localhost:3000/auth/callback"]
  logout_urls                          = ["http://localhost:3000/"]
  explicit_auth_flows                  = ["ALLOW_REFRESH_TOKEN_AUTH", "ALLOW_USER_SRP_AUTH"]
}

resource "aws_cognito_user_pool_domain" "hosted" {
  count        = var.enable_resources && var.enable_identity ? 1 : 0
  domain       = "${var.name_prefix}-${local.suffix}"
  user_pool_id = aws_cognito_user_pool.users[0].id
}

resource "aws_guardduty_detector" "reference" {
  count                        = var.enable_resources && var.enable_guardduty ? 1 : 0
  enable                       = true
  finding_publishing_frequency = "FIFTEEN_MINUTES"
  tags                         = merge(local.common_tags, { Purpose = "optional-threat-detection-reference" })
}
