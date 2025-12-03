# Root Module Variables
# Set these values in terraform.tfvars

# =============================================================================
# AWS Configuration
# =============================================================================

variable "region" {
  description = "AWS region where resources will be created"
  type        = string
}

variable "environment" {
  description = "Environment name (e.g., production, staging, development)"
  type        = string
  default     = "production"
}

# =============================================================================
# Transit Gateway Configuration
# =============================================================================

variable "transit_gateway_name" {
  description = "Name tag for Transit Gateway"
  type        = string
}

variable "transit_gateway_description" {
  description = "Description for Transit Gateway"
  type        = string
  default     = "Managed by Terraform"
}

variable "transit_gateway_amazon_side_asn" {
  description = "Amazon side ASN for Transit Gateway"
  type        = number
  default     = 64512
}

variable "transit_gateway_auto_accept_shared_attachments" {
  description = "Whether resource attachment requests are automatically accepted"
  type        = string
  default     = "enable"
}

variable "transit_gateway_default_route_table_association" {
  description = "Whether resource attachments are automatically associated with the default route table"
  type        = string
  default     = "disable"
}

variable "transit_gateway_default_route_table_propagation" {
  description = "Whether resource attachments automatically propagate routes to the default route table"
  type        = string
  default     = "disable"
}

variable "transit_gateway_dns_support" {
  description = "Whether DNS support is enabled"
  type        = string
  default     = "enable"
}

variable "transit_gateway_vpn_ecmp_support" {
  description = "Whether VPN ECMP support is enabled"
  type        = string
  default     = "enable"
}

# =============================================================================
# Route Tables
# =============================================================================

variable "route_tables" {
  description = "Map of Transit Gateway route tables to create"
  type = map(object({
    name = string
    tags = optional(map(string), {})
  }))
}

# =============================================================================
# VPC Attachments
# =============================================================================

variable "vpc_attachments" {
  description = "Map of VPC attachments to Transit Gateway"
  type = map(object({
    name                   = string
    vpc_id                 = string
    subnet_ids             = list(string)
    appliance_mode_support = optional(string, "disable")
    dns_support            = optional(string, "enable")
    ipv6_support           = optional(string, "disable")
    tags                   = optional(map(string), {})
  }))
}

# =============================================================================
# Route Table Associations & Propagations
# =============================================================================

variable "route_table_associations" {
  description = "Map of route table associations (which attachment uses which route table)"
  type = map(object({
    route_table_key = string
    attachment_key  = string
  }))
}

variable "route_table_propagations" {
  description = "Map of route table propagations (which route table receives routes from which attachment)"
  type = map(object({
    route_table_key = string
    attachment_key  = string
  }))
}

# =============================================================================
# Routes
# =============================================================================

variable "tgw_routes" {
  description = "Map of Transit Gateway routes (static routes within TGW route tables)"
  type = map(object({
    destination_cidr_block = string
    route_table_key        = string
    attachment_key         = optional(string)
    blackhole              = optional(bool, false)
  }))
}

variable "vpc_routes" {
  description = "Map of VPC routes pointing to Transit Gateway"
  type = map(object({
    route_table_id         = string
    destination_cidr_block = string
  }))
}

# =============================================================================
# Tags
# =============================================================================

variable "tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    ManagedBy = "Terraform"
  }
}
