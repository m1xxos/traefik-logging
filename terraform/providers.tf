terraform {
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "0.111.1"
    }
    infisical = {
      source  = "Infisical/infisical"
      version = "0.18.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "2.9.1"
    }
  }
  # bucket, access_key and secret_key come from yc.auto.tfvars via
  # `terraform init -backend-config=yc.auto.tfvars` (task tfinit): terraform
  # does not allow variables inside the backend block.
  backend "s3" {
    endpoint                    = "https://storage.yandexcloud.net"
    region                      = "ru-central1"
    key                         = "traefik-logging.tfstate"
    skip_region_validation      = true
    skip_credentials_validation = true
    skip_requesting_account_id  = true
    skip_s3_checksum            = true
  }
}

provider "infisical" {
  host = "https://infisical.home.m1xxos.online"
  auth = {
    universal = {
      client_id     = var.infisical_id
      client_secret = var.infisical_secret
    }
  }
}

provider "proxmox" {
  endpoint  = ephemeral.infisical_secret.proxmox_api_url.value
  username  = ephemeral.infisical_secret.proxmox_api_token_id.value
  api_token = ephemeral.infisical_secret.proxmox_api_token.value
  insecure  = true

  ssh {
    agent    = true
    username = "root"
    password = ephemeral.infisical_secret.proxmox_ssh_password.value
  }
}
