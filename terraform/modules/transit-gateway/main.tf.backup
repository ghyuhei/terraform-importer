# Transit Gateway Module
# This module manages AWS Transit Gateway and related resources

# Transit Gateway Route Table Associations (Dynamic with for_each)
resource "aws_ec2_transit_gateway_route_table_association" "this" {
  for_each = var.route_table_associations

  transit_gateway_attachment_id  = aws_ec2_transit_gateway_vpc_attachment.this[each.value.attachment_key].id
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.this[each.value.route_table_key].id
}

# Transit Gateway Route Table Propagations (Dynamic with for_each)
resource "aws_ec2_transit_gateway_route_table_propagation" "this" {
  for_each = var.route_table_propagations

  transit_gateway_attachment_id  = aws_ec2_transit_gateway_vpc_attachment.this[each.value.attachment_key].id
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.this[each.value.route_table_key].id
}


# Transit Gateway VPC Attachments (Dynamic with for_each)
resource "aws_ec2_transit_gateway_vpc_attachment" "this" {
  for_each = var.vpc_attachments

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
    var.tags,
    {
      Name = each.value.name
    },
    try(each.value.tags, {})
  )
}


# Transit Gateway Route Tables (Dynamic with for_each)
resource "aws_ec2_transit_gateway_route_table" "this" {
  for_each = var.route_tables

  transit_gateway_id = aws_ec2_transit_gateway.this.id

  tags = merge(
    var.tags,
    {
      Name = each.value.name
    },
    try(each.value.tags, {})
  )
}


# Transit Gateway Routes (Dynamic with for_each)
resource "aws_ec2_transit_gateway_route" "this" {
  for_each = var.tgw_routes

  destination_cidr_block         = each.value.destination_cidr_block
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.this[each.value.route_table_key].id
  transit_gateway_attachment_id  = try(each.value.attachment_key != null ? aws_ec2_transit_gateway_vpc_attachment.this[each.value.attachment_key].id : null, null)
  blackhole                      = try(each.value.blackhole, false)
}


# Transit Gateway
resource "aws_ec2_transit_gateway" "this" {
  description                     = var.transit_gateway_description
  amazon_side_asn                 = var.transit_gateway_amazon_side_asn
  default_route_table_association = var.transit_gateway_default_route_table_association
  default_route_table_propagation = var.transit_gateway_default_route_table_propagation
  dns_support                     = var.transit_gateway_dns_support
  vpn_ecmp_support                = var.transit_gateway_vpn_ecmp_support
  auto_accept_shared_attachments  = var.transit_gateway_auto_accept_shared_attachments

  tags = merge(
    var.tags,
    {
      Name = var.transit_gateway_name
    }
  )
}


# VPC Routes to Transit Gateway (Dynamic with for_each)
resource "aws_route" "this" {
  for_each = var.vpc_routes

  route_table_id         = each.value.route_table_id
  destination_cidr_block = each.value.destination_cidr_block
  transit_gateway_id     = aws_ec2_transit_gateway.this.id
}


