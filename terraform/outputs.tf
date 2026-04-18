output "k3s_control_plane_ip" { value = var.k3s_cp_ip }
output "k3s_worker_ips"       { value = var.k3s_worker_ips }

output "next_steps" {
  value = <<-EOT

    VMs created! Next:
      1. Run: mise run k3s-install
         (Ansible installs k3s and writes kubeconfig to ~/.kube/config)
      2. Run: mise run gitops

    IPs:  CP=${var.k3s_cp_ip}  W1=${var.k3s_worker_ips[0]}  W2=${var.k3s_worker_ips[1]}
  EOT
}
