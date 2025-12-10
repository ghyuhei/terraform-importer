# Transit Gateway Route Table
resource "aws_ec2_transit_gateway_route_table" "this" {
  transit_gateway_id = local.transit_gateway_id

  tags = merge(
    local.common_tags,
    local.route_table_tags,
    {
      Name = local.route_table_name
    }
  )
}

# Route Table Associations
resource "aws_ec2_transit_gateway_route_table_association" "this" {
  for_each = local.associations

  transit_gateway_attachment_id = (
    each.value.attachment_type == "vpc" ? local.vpc_attachment_ids[each.value.attachment_key] :
    each.value.attachment_type == "peering" ? local.peering_attachment_ids[each.value.attachment_key] :
    each.value.attachment_type == "peering_accepter" ? local.peering_accepter_attachment_ids[each.value.attachment_key] :
    each.value.attachment_type == "vpn" ? local.vpn_attachment_ids[each.value.attachment_key] :
    each.value.attachment_type == "dx_gateway" ? local.dx_gateway_attachment_ids[each.value.attachment_key] :
    each.value.attachment_type == "network_function" ? local.network_function_attachment_ids[each.value.attachment_key] :
    null
  )
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.this.id
}

# Route Table Propagations
resource "aws_ec2_transit_gateway_route_table_propagation" "this" {
  for_each = local.propagations

  transit_gateway_attachment_id = (
    each.value.attachment_type == "vpc" ? local.vpc_attachment_ids[each.value.attachment_key] :
    each.value.attachment_type == "peering" ? local.peering_attachment_ids[each.value.attachment_key] :
    each.value.attachment_type == "peering_accepter" ? local.peering_accepter_attachment_ids[each.value.attachment_key] :
    each.value.attachment_type == "vpn" ? local.vpn_attachment_ids[each.value.attachment_key] :
    each.value.attachment_type == "dx_gateway" ? local.dx_gateway_attachment_ids[each.value.attachment_key] :
    each.value.attachment_type == "network_function" ? local.network_function_attachment_ids[each.value.attachment_key] :
    null
  )
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.this.id
}

# Transit Gateway Routes
resource "aws_ec2_transit_gateway_route" "this" {
  for_each = local.tgw_routes

  destination_cidr_block         = each.value.destination_cidr_block
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.this.id

  transit_gateway_attachment_id = try(each.value.blackhole, false) ? null : (
    each.value.attachment_type == "vpc" ? local.vpc_attachment_ids[each.value.attachment_key] :
    each.value.attachment_type == "peering" ? local.peering_attachment_ids[each.value.attachment_key] :
    each.value.attachment_type == "peering_accepter" ? local.peering_accepter_attachment_ids[each.value.attachment_key] :
    each.value.attachment_type == "vpn" ? local.vpn_attachment_ids[each.value.attachment_key] :
    each.value.attachment_type == "dx_gateway" ? local.dx_gateway_attachment_ids[each.value.attachment_key] :
    each.value.attachment_type == "network_function" ? local.network_function_attachment_ids[each.value.attachment_key] :
    null
  )

  blackhole = try(each.value.blackhole, false)
}
