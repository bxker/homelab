# ── Ubuntu Cloud Image ──

resource "proxmox_virtual_environment_download_file" "ubuntu_noble" {
  content_type        = "iso"
  datastore_id        = "local"
  node_name           = var.proxmox_node
  url                 = "https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img"
  file_name           = "noble-server-cloudimg-amd64.img"
  overwrite_unmanaged = true
}

# ── Control Plane ──

resource "proxmox_virtual_environment_vm" "k3s_cp" {
  name      = "k3s-cp-1"
  node_name = var.proxmox_node
  vm_id     = 100
  tags      = ["k3s", "kubernetes", "control-plane"]

  cpu {
    cores = var.k3s_cp_cores
    type  = "x86-64-v2-AES"
  }

  memory { dedicated = var.k3s_cp_memory }

  disk {
    datastore_id = var.storage_pool
    file_id      = proxmox_virtual_environment_download_file.ubuntu_noble.id
    interface    = "scsi0"
    size         = var.k3s_cp_disk
    iothread     = true
    discard      = "on"
    ssd          = true
  }

  network_device {
    bridge = var.network_bridge
    model  = "virtio"
  }

  initialization {
    ip_config {
      ipv4 {
        address = "${var.k3s_cp_ip}/24"
        gateway = var.network_gateway
      }
    }
    dns {
      servers = ["192.168.1.1", "1.1.1.1"]
    }
    user_account {
      username = "ubuntu"
      keys     = [var.ssh_public_key]
    }
  }

  bios       = "ovmf"
  efi_disk {
    datastore_id = var.storage_pool
    file_format  = "raw"
    type         = "4m"
  }

  operating_system { type = "l26" }
  on_boot = true
  machine = "q35"
}

# ── Workers ──

resource "proxmox_virtual_environment_vm" "k3s_workers" {
  count     = length(var.k3s_worker_ips)
  name      = "k3s-worker-${count.index + 1}"
  node_name = var.proxmox_node
  vm_id     = 101 + count.index
  tags      = ["k3s", "kubernetes", "worker"]

  cpu {
    cores = var.k3s_worker_cores
    type  = "x86-64-v2-AES"
  }

  memory { dedicated = var.k3s_worker_memory }

  disk {
    datastore_id = var.storage_pool
    file_id      = proxmox_virtual_environment_download_file.ubuntu_noble.id
    interface    = "scsi0"
    size         = var.k3s_worker_disk
    iothread     = true
    discard      = "on"
    ssd          = true
  }

  network_device {
    bridge = var.network_bridge
    model  = "virtio"
  }

  initialization {
    ip_config {
      ipv4 {
        address = "${var.k3s_worker_ips[count.index]}/24"
        gateway = var.network_gateway
      }
    }
    dns {
      servers = ["192.168.1.1", "1.1.1.1"]
    }
    user_account {
      username = "ubuntu"
      keys     = [var.ssh_public_key]
    }
  }

  bios = "ovmf"
  efi_disk {
    datastore_id = var.storage_pool
    file_format  = "raw"
    type         = "4m"
  }

  operating_system { type = "l26" }
  on_boot = true
  machine = "q35"
}
