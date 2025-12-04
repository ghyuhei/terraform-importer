# Module Outputs

output "transit_gateway_id" {
  description = "Transit Gateway ID"
  value       = try(aws_ec2_transit_gateway.this.id, null)
}

output "transit_gateway_arn" {
  description = "Transit Gateway ARN"
  value       = try(aws_ec2_transit_gateway.this.arn, null)
}

output "transit_gateway_owner_id" {
  description = "Transit Gateway Owner ID"
  value       = try(aws_ec2_transit_gateway.this.owner_id, null)
}

output "route_table_ids" {
  description = "Map of route table names to IDs"
  value = {
    for k, v in aws_ec2_transit_gateway_route_table.this : k => v.id
  }
}

output "vpc_attachment_ids" {
  description = "Map of VPC attachment names to IDs"
  value = {
    for k, v in aws_ec2_transit_gateway_vpc_attachment.this : k => v.id
  }
}

output "peering_attachment_ids" {
  description = "Map of peering attachment names to IDs"
  value = {
    for k, v in aws_ec2_transit_gateway_peering_attachment.this : k => v.id
  }
}
