variable "proxmox_url" {
  description = "Proxmox API URL (e.g., https://192.168.1.10:8006)"
  type        = string
}

variable "proxmox_api_token" {
  description = "API token: user@realm!tokenid=secret"
  type        = string
  sensitive   = true
}

variable "proxmox_node" {
  type    = string
  default = "pve"
}

variable "network_bridge" {
  type    = string
  default = "vmbr0"
}

variable "network_gateway" {
  type    = string
  default = "192.168.1.254"
}

variable "ssh_public_key" {
  description = "SSH public key injected into VMs via cloud-init"
  type        = string
}

variable "k3s_cp_ip" {
  type    = string
  default = "192.168.1.100"
}

variable "k3s_worker_ips" {
  type    = list(string)
  default = ["192.168.1.101", "192.168.1.102"]
}

variable "k3s_cp_cores" {
  type    = number
  default = 2
}

variable "k3s_cp_memory" {
  type    = number
  default = 4096
}

variable "k3s_cp_disk" {
  type    = number
  default = 20
}

variable "k3s_worker_cores" {
  type    = number
  default = 2
}

variable "k3s_worker_memory" {
  type    = number
  default = 8192
}

variable "k3s_worker_disk" {
  type    = number
  default = 60
}

variable "storage_pool" {
  type    = string
  default = "local-lvm"
}
