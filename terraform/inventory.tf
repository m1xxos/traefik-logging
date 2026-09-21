# The inventory is the only generated file: ansible needs to know which backend
# and mode the VMs were created for, and terraform is the one that knows.
resource "local_file" "inventory" {
  filename        = "${path.module}/../ansible/inventory.yaml"
  file_permission = "0644"
  content = templatefile("${path.module}/inventory.tftpl", {
    vms     = local.vms
    backend = var.backend
    mode    = var.mode
  })
}
