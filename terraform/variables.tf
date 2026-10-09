variable "prefix" {
  type        = string
  default     = "rbcopilot"
  description = "Name prefix for all resources (lowercase letters and digits)"
}

variable "suffix" {
  type        = string
  description = "Short unique suffix so the registry name is globally unique, e.g. your initials + digits"
}

variable "location" {
  type    = string
  default = "centralindia"
}

variable "node_vm_size" {
  type    = string
  default = "Standard_B2s"
}
