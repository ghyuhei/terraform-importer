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

# Peering Attachments
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

# VPN Connections
resource "aws_vpn_connection" "this" {
  for_each = local.vpn_attachments

  customer_gateway_id = each.value.customer_gateway_id
  transit_gateway_id  = aws_ec2_transit_gateway.this.id
  type                = try(each.value.type, "ipsec.1")
  static_routes_only  = try(each.value.static_routes_only, false)

  tags = merge(
    local.tags,
    {
      Name = each.value.name
    },
    try(each.value.tags, {})
  )
}

# Direct Connect Gateway Associations
resource "aws_dx_gateway_association" "this" {
  for_each = local.dx_gateway_attachments

  dx_gateway_id         = each.value.dx_gateway_id
  associated_gateway_id = aws_ec2_transit_gateway.this.id

  allowed_prefixes = try(each.value.allowed_prefixes, null)
}
