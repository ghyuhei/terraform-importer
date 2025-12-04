# Root Module Outputs

output "transit_gateway_id" {
  description = "Transit Gateway ID"
  value       = module.transit_gateway.transit_gateway_id
}

output "transit_gateway_arn" {
  description = "Transit Gateway ARN"
  value       = module.transit_gateway.transit_gateway_arn
}

output "route_table_ids" {
  description = "Transit Gateway Route Table IDs"
  value       = module.transit_gateway.route_table_ids
}

output "vpc_attachment_ids" {
  description = "VPC Attachment IDs"
  value       = module.transit_gateway.vpc_attachment_ids
}

output "peering_attachment_ids" {
  description = "Map of peering attachment names to IDs"
  value       = module.transit_gateway.peering_attachment_ids
}
