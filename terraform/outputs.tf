output "vms" {
  value = { for name, vm in local.vms : name => vm.ip }
}

output "grafana" {
  value = "http://${local.base_vms["control-1"].ip}:3000"
}

output "loadgen" {
  value = "http://${local.base_vms["control-1"].ip}:8000"
}

output "backend_ui" {
  value = var.backend == "none" ? null : {
    victorialogs = "http://192.168.1.63:${var.mode == "cluster" ? "9471" : "9428"}/select/vmui"
    loki         = "http://192.168.1.63:3100/ready"
    elk          = "http://192.168.1.63:5601"
    openobserve  = "http://192.168.1.63:5080"
  }[var.backend]
}
