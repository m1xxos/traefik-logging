locals {
  node_name    = "plusha"
  datastore_id = "pve-nvme"
  gateway      = "192.168.1.1"

  base_vms = {
    control-1 = {
      role   = "control"
      vm_id  = 600
      ip     = "192.168.1.60"
      cores  = 2
      memory = 3072
      disk   = 30
    }
    traefik-1 = {
      role   = "traefik"
      vm_id  = 601
      ip     = "192.168.1.61"
      cores  = 4
      memory = 8192
      disk   = 30
    }
    traefik-2 = {
      role   = "traefik"
      vm_id  = 602
      ip     = "192.168.1.62"
      cores  = 4
      memory = 8192
      disk   = 30
    }
  }

  # 9 GiB for the backend in both modes so single and cluster compare like for
  # like. backend-1 is bigger in cluster mode because it also carries the shared
  # pieces (kibana, minio, nats, postgres, vlinsert/vlselect).
  backend_vms = var.backend == "none" ? {} : (
    var.mode == "single" ? {
      backend-1 = {
        role   = "backend"
        vm_id  = 603
        ip     = "192.168.1.63"
        cores  = 6
        memory = 9216
        disk   = 60
      }
      } : {
      backend-1 = {
        role   = "backend"
        vm_id  = 603
        ip     = "192.168.1.63"
        cores  = 2
        memory = 3584
        disk   = 60
      }
      backend-2 = {
        role   = "backend"
        vm_id  = 604
        ip     = "192.168.1.64"
        cores  = 2
        memory = 2816
        disk   = 40
      }
      backend-3 = {
        role   = "backend"
        vm_id  = 605
        ip     = "192.168.1.65"
        cores  = 2
        memory = 2816
        disk   = 40
      }
    }
  )

  vms = merge(local.base_vms, local.backend_vms)
}

resource "proxmox_virtual_environment_vm" "vm" {
  for_each      = local.vms
  name          = each.key
  description   = "Managed by Terraform, traefik-logging bench"
  tags          = ["traefik-logging", each.value.role]
  node_name     = local.node_name
  vm_id         = each.value.vm_id
  on_boot       = true
  started       = true
  scsi_hardware = "virtio-scsi-single"

  cpu {
    cores = each.value.cores
    type  = "host"
  }

  memory {
    dedicated = each.value.memory
  }

  agent {
    enabled = true
  }

  network_device {
    bridge = "vmbr0"
  }

  disk {
    datastore_id = local.datastore_id
    file_id      = proxmox_download_file.ubuntu_noble_cloudimg.id
    file_format  = "raw"
    interface    = "scsi0"
    size         = each.value.disk
    iothread     = true
    discard      = "on"
    cache        = "writeback"
  }

  serial_device {
    device = "socket"
  }

  operating_system {
    type = "l26"
  }

  initialization {
    datastore_id      = local.datastore_id
    user_data_file_id = proxmox_virtual_environment_file.cloud_init[each.key].id

    ip_config {
      ipv4 {
        address = "${each.value.ip}/24"
        gateway = local.gateway
      }
      ipv6 {
        address = "dhcp"
      }
    }
  }
}
