variable "aws_region" {
  description = "Comparison region only; choose a region only after data-residency and cost review."
  type        = string
  default     = "us-east-1"
}

variable "enable_resources" {
  description = "Must remain false unless the exact account-specific cost and deployment review has been approved."
  type        = bool
  default     = false
}

variable "enable_identity" {
  description = "Include the optional Cognito user pool when resources are deliberately enabled."
  type        = bool
  default     = false
}

variable "enable_guardduty" {
  description = "Include the optional GuardDuty detector when resources are deliberately enabled. Usage may incur charges."
  type        = bool
  default     = false
}

variable "name_prefix" {
  description = "Lowercase, globally unique prefix for S3 bucket names. Change only during an approved deployment review."
  type        = string
  default     = "cloudvault-reference"

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{2,35}$", var.name_prefix))
    error_message = "name_prefix must be 3-36 lowercase letters, numbers, or hyphens and begin with a letter or number."
  }
}

variable "retention_days" {
  description = "Short lifecycle retention for temporary portfolio objects and logs."
  type        = number
  default     = 7

  validation {
    condition     = var.retention_days >= 1 && var.retention_days <= 30
    error_message = "retention_days must be from 1 through 30."
  }
}
