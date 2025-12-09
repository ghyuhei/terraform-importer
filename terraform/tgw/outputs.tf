# Output Transit Gateway ID and attachment IDs for use by route table directories
output "transit_gateway_id" {
  description = "Transit Gateway ID"
  value       = aws_ec2_transit_gateway.this.id
}

output "transit_gateway_arn" {
  description = "Transit Gateway ARN"
  value       = aws_ec2_transit_gateway.this.arn
}

output "region" {
  description = "AWS Region"
  value       = local.region
}

output "tags" {
  description = "Common tags"
  value       = local.tags
}

# Output all attachment IDs for reference by route tables
output "vpc_attachment_ids" {
  description = "Map of VPC attachment keys to IDs"
  value       = { for k, v in aws_ec2_transit_gateway_vpc_attachment.this : k => v.id }
}

output "peering_attachment_ids" {
  description = "Map of peering attachment keys to IDs (Requester side)"
  value       = { for k, v in aws_ec2_transit_gateway_peering_attachment.this : k => v.id }
}

output "peering_accepter_attachment_ids" {
  description = "Map of peering accepter attachment keys to IDs (Accepter side - from data source)"
  value       = { for k, v in data.aws_ec2_transit_gateway_attachment.peering_accepter : k => v.id }
}

output "vpn_attachment_ids" {
  description = "Map of VPN attachment keys to attachment IDs (from data source)"
  value       = { for k, v in data.aws_ec2_transit_gateway_attachment.vpn : k => v.id }
}

output "dx_gateway_attachment_ids" {
  description = "Map of DX Gateway attachment keys to attachment IDs (from data source)"
  value       = { for k, v in data.aws_ec2_transit_gateway_attachment.dx_gateway : k => v.id }
}
