variable "bucket" {
  type = string
}

variable "access_key" {
  type      = string
  sensitive = true
}

variable "secret_key" {
  type      = string
  sensitive = true
}

variable "infisical_id" {
  type      = string
  sensitive = true
}

variable "infisical_secret" {
  type      = string
  sensitive = true
}

variable "infisical_workspace_id" {
  type    = string
  default = "cc160c9f-8470-482f-a8da-350d68337f48"
}

variable "backend" {
  type        = string
  description = "Log backend under test; none keeps only traefik and control VMs"
  default     = "none"
  validation {
    condition     = contains(["none", "victorialogs", "loki", "elk", "openobserve"], var.backend)
    error_message = "backend must be one of none, victorialogs, loki, elk, openobserve"
  }
}

variable "mode" {
  type    = string
  default = "single"
  validation {
    condition     = contains(["single", "cluster"], var.mode)
    error_message = "mode must be single or cluster"
  }
}
