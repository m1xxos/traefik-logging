resource "proxmox_download_file" "ubuntu_noble_cloudimg" {
  content_type = "iso"
  datastore_id = "local"
  node_name    = local.node_name
  file_name    = "ubuntu-24.04-noble-cloudimg-amd64.img"
  url          = "https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img"
  overwrite    = false
}

# Docker and the stacks come from ansible; cloud-init only has to make the
# VM reachable (ssh key) and let proxmox see it (guest agent).
resource "proxmox_virtual_environment_file" "cloud_init" {
  for_each     = local.vms
  content_type = "snippets"
  datastore_id = "local"
  node_name    = local.node_name

  source_raw {
    file_name = "traefik-logging-${each.key}.yaml"
    data      = <<-EOT
      #cloud-config
      hostname: ${each.key}
      users:
        - name: m1xxos
          sudo: ALL=(ALL) NOPASSWD:ALL
          groups: [sudo]
          shell: /bin/bash
          ssh_authorized_keys:
            - ${file(pathexpand("~/.ssh/id_rsa.pub"))}
      package_update: true
      packages:
        - qemu-guest-agent
      runcmd:
        - systemctl enable --now qemu-guest-agent
    EOT
  }
}
