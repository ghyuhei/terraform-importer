# Root Module - Transit Gateway Infrastructure

module "transit_gateway" {
  source = "./modules/transit-gateway"

  # Transit Gateway configuration
  transit_gateway_name                           = var.transit_gateway_name
  transit_gateway_description                    = var.transit_gateway_description
  transit_gateway_amazon_side_asn                = var.transit_gateway_amazon_side_asn
  transit_gateway_auto_accept_shared_attachments = var.transit_gateway_auto_accept_shared_attachments
  transit_gateway_default_route_table_association = var.transit_gateway_default_route_table_association
  transit_gateway_default_route_table_propagation = var.transit_gateway_default_route_table_propagation
  transit_gateway_dns_support                    = var.transit_gateway_dns_support
  transit_gateway_vpn_ecmp_support              = var.transit_gateway_vpn_ecmp_support

  # Route tables, attachments, and associations
  route_tables              = var.route_tables
  vpc_attachments           = var.vpc_attachments
  route_table_associations  = var.route_table_associations
  route_table_propagations  = var.route_table_propagations

  # Routes
  tgw_routes = var.tgw_routes
  vpc_routes = var.vpc_routes

  # Tags
  tags = var.tags
}
