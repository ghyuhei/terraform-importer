# Transit Gateway
resource "aws_ec2_transit_gateway" "this" {
  description                     = local.transit_gateway.description
  amazon_side_asn                 = local.transit_gateway.amazon_side_asn
  default_route_table_association = local.transit_gateway.default_route_table_association
  default_route_table_propagation = local.transit_gateway.default_route_table_propagation
  dns_support                     = local.transit_gateway.dns_support
  vpn_ecmp_support                = local.transit_gateway.vpn_ecmp_support
  auto_accept_shared_attachments  = local.transit_gateway.auto_accept_shared_attachments

  tags = merge(
    local.tags,
    {
      Name = local.transit_gateway.name
    }
  )
}

# VPC Attachments
resource "aws_ec2_transit_gateway_vpc_attachment" "this" {
  for_each = local.vpc_attachments

  transit_gateway_id = aws_ec2_transit_gateway.this.id
  vpc_id             = each.value.vpc_id
  subnet_ids         = each.value.subnet_ids

  appliance_mode_support = try(each.value.appliance_mode_support, "disable")
  dns_support            = try(each.value.dns_support, "enable")
  ipv6_support           = try(each.value.ipv6_support, "disable")

  lifecycle {
    ignore_changes = [subnet_ids, appliance_mode_support, dns_support, ipv6_support]
  }

  tags = merge(
    local.tags,
    {
      Name = each.value.name
    },
    try(each.value.tags, {})
  )
}

# Peering Attachments (Requester side)
resource "aws_ec2_transit_gateway_peering_attachment" "this" {
  for_each = local.peering_attachments

  transit_gateway_id      = aws_ec2_transit_gateway.this.id
  peer_transit_gateway_id = each.value.peer_transit_gateway_id
  peer_region             = each.value.peer_region
  peer_account_id         = try(each.value.peer_account_id, null)

  tags = merge(
    local.tags,
    {
      Name = each.value.name
    },
    try(each.value.tags, {})
  )
}

# Peering Accepter Attachments (Accepter side - read-only)
data "aws_ec2_transit_gateway_attachment" "peering_accepter" {
  for_each = local.peering_accepter_attachments

  transit_gateway_attachment_id = each.value.attachment_id
}

# VPN Attachments (read-only)
data "aws_ec2_transit_gateway_attachment" "vpn" {
  for_each = local.vpn_attachments

  transit_gateway_attachment_id = each.value.attachment_id
}

# Direct Connect Gateway Attachments (read-only)
data "aws_ec2_transit_gateway_attachment" "dx_gateway" {
  for_each = local.dx_gateway_attachments

  transit_gateway_attachment_id = each.value.attachment_id
}

# Network Function Attachments (read-only)
data "aws_ec2_transit_gateway_attachment" "network_function" {
  for_each = local.network_function_attachments

  transit_gateway_attachment_id = each.value.attachment_id
}
