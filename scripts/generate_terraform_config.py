#!/usr/bin/env python3
"""Terraform Configuration Generator for route-table-based directory structure.

Generates Terraform configuration split by route tables:
- terraform/tgw/ : Transit Gateway resource
- terraform/rt-{name}/ : Each route table with its attachments

Supports multi-account and multi-region environments.

Requirements: Python 3.8+
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Constants
DEFAULT_INPUT_DIR = './output'
DEFAULT_OUTPUT_DIR = './terraform'

# Static file templates
VERSIONS_TF = """terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }

  # Uncomment and configure for remote state storage
  # backend "s3" {
  #   bucket = "my-terraform-state"
  #   key    = "tgw/{account_id}/{region}/rt-{name}/terraform.tfstate"
  #   region = "ap-northeast-1"
  # }
}

provider "aws" {
  region = local.region
}
"""

DATA_TF = """# Reference Transit Gateway and Attachments
#
# For local backend (default):
#   Use relative path to tgw directory
#
# For remote backend (S3, etc):
#   Update the backend and config blocks below to match your backend configuration
#   Example for S3:
#   backend = "s3"
#   config = {
#     bucket = "my-terraform-state"
#     key    = "tgw/{account_id}/{region}/tgw/terraform.tfstate"
#     region = "ap-northeast-1"
#   }
data "terraform_remote_state" "tgw" {
  backend = "local"

  config = {
    path = "../tgw/terraform.tfstate"
  }
}

locals {
  transit_gateway_id = data.terraform_remote_state.tgw.outputs.transit_gateway_id
  region             = data.terraform_remote_state.tgw.outputs.region
  common_tags        = data.terraform_remote_state.tgw.outputs.tags

  # Reference all attachments from tgw module
  vpc_attachment_ids        = try(data.terraform_remote_state.tgw.outputs.vpc_attachment_ids, {})
  peering_attachment_ids    = try(data.terraform_remote_state.tgw.outputs.peering_attachment_ids, {})
  vpn_attachment_ids        = try(data.terraform_remote_state.tgw.outputs.vpn_attachment_ids, {})
  dx_gateway_attachment_ids = try(data.terraform_remote_state.tgw.outputs.dx_gateway_attachment_ids, {})
}
"""

MAIN_TF_TGW = """# Transit Gateway
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

# VPN Attachments - Use data source for existing VPN connections
# VPN attachments are automatically created when VPN connection is associated with TGW
# These cannot be imported separately - they are managed through aws_vpn_connection
# If you need to manage VPN connections with Terraform, create aws_vpn_connection resources separately
data "aws_ec2_transit_gateway_attachment" "vpn" {
  for_each = local.vpn_attachments

  transit_gateway_attachment_id = each.value.attachment_id
}

# Direct Connect Gateway Attachments - Use data source for existing DX Gateway associations
# DX Gateway attachments are automatically created when DX Gateway is associated with TGW
# These cannot be imported separately - they are managed through aws_dx_gateway_association
# If you need to manage DX Gateway associations with Terraform, create aws_dx_gateway_association resources separately
data "aws_ec2_transit_gateway_attachment" "dx_gateway" {
  for_each = local.dx_gateway_attachments

  transit_gateway_attachment_id = each.value.attachment_id
}
"""

MAIN_TF_RT = """# Transit Gateway Route Table
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
    each.value.attachment_type == "vpn" ? local.vpn_attachment_ids[each.value.attachment_key] :
    each.value.attachment_type == "dx_gateway" ? local.dx_gateway_attachment_ids[each.value.attachment_key] :
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
    each.value.attachment_type == "vpn" ? local.vpn_attachment_ids[each.value.attachment_key] :
    each.value.attachment_type == "dx_gateway" ? local.dx_gateway_attachment_ids[each.value.attachment_key] :
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
    each.value.attachment_type == "vpn" ? local.vpn_attachment_ids[each.value.attachment_key] :
    each.value.attachment_type == "dx_gateway" ? local.dx_gateway_attachment_ids[each.value.attachment_key] :
    null
  )

  blackhole = try(each.value.blackhole, false)
}
"""


class TerraformConfigGeneratorV2:
    """Generator for split Terraform configuration."""

    def __init__(self, input_dir: str, output_dir: str, account_id: str = None, region: str = None) -> None:
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.account_id = account_id
        self.region = region
        self.selected_tgw_id = None  # Will be set when selecting TGW

    def load_json(self, filename: str) -> dict:
        """Load JSON file from input directory."""
        filepath = self.input_dir / filename
        if not filepath.exists():
            return {}
        with open(filepath, encoding='utf-8') as f:
            return json.load(f)

    def get_tag_value(self, tags: List[dict] | None, key: str, default: str = "") -> str:
        """Extract tag value from AWS tags list."""
        if not tags:
            return default
        for tag in tags:
            if tag.get('Key') == key:
                return tag.get('Value', default)
        return default

    def sanitize_key(self, name: str) -> str:
        """Sanitize resource name for use as Terraform map key."""
        return name.replace('-', '_').replace(' ', '_').replace(':', '_').lower()

    def sanitize_dirname(self, name: str) -> str:
        """Sanitize route table name for directory name.
        
        Examples:
            tgw-rt-production -> rt-production
            TGW-RT-Shared -> rt-shared
        """
        # Remove tgw-rt- prefix (case insensitive)
        name = re.sub(r'^tgw-rt-', '', name, flags=re.IGNORECASE)
        return name.replace(' ', '-').replace('_', '-').lower()

    def format_hcl_value(self, value: Any, indent: int = 0) -> str:
        """Format a value as HCL."""
        indent_str = "  " * indent

        if isinstance(value, dict):
            if not value:
                return "{}"
            lines = ["{"]
            for k, v in value.items():
                formatted = self.format_hcl_value(v, indent + 1)
                lines.append(f'{indent_str}  {k} = {formatted}')
            lines.append(f'{indent_str}}}')
            return '\n'.join(lines)
        elif isinstance(value, list):
            if not value:
                return "[]"
            return json.dumps(value)
        elif isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, (int, float)):
            return str(value)
        elif value is None:
            return "null"
        else:
            # Escape quotes in strings
            escaped = str(value).replace('"', '\\"')
            return f'"{escaped}"'

    def generate_shared_locals(self) -> str:
        """Generate shared/locals.tf content."""
        tgws_data = self.load_json('transit-gateways.json')
        tgws = tgws_data.get('TransitGateways', [])

        if not tgws:
            raise ValueError("No Transit Gateway found")

        # Select TGW with custom route tables (DefaultRouteTableAssociation = disable)
        # These are typically the ones users want to manage with Terraform
        selected_tgw = None
        for tgw in tgws:
            options = tgw.get('Options', {})
            if options.get('DefaultRouteTableAssociation') == 'disable':
                selected_tgw = tgw
                break

        # Fallback to first TGW if none found with disable
        if not selected_tgw:
            selected_tgw = tgws[0]
            if len(tgws) > 1:
                print(f"⚠ Multiple TGWs found. Using: {selected_tgw.get('TransitGatewayId')}")

        tgw = selected_tgw
        self.selected_tgw_id = tgw['TransitGatewayId']  # Store selected TGW ID
        options = tgw.get('Options', {})

        # Use provided region or extract from TGW owner ID
        region = self.region if self.region else "ap-northeast-1"
        account_id = self.account_id if self.account_id else tgw.get('OwnerId', '')

        tgw_name = self.get_tag_value(tgw.get('Tags'), 'Name', 'tgw')
        tgw_desc = options.get('Description', 'Transit Gateway')
        tgw_asn = options.get('AmazonSideAsn', 64512)

        lines = ["# Shared configuration for Transit Gateway", "locals {"]
        lines.append(f'  region      = "{region}"')
        lines.append(f'  account_id  = "{account_id}"')
        lines.append('  environment = "production"')
        lines.append("")
        lines.append("  # Transit Gateway configuration")
        lines.append("  transit_gateway = {")
        lines.append(f'    name                            = "{tgw_name}"')
        lines.append(f'    description                     = "{tgw_desc}"')
        lines.append(f'    amazon_side_asn                 = {tgw_asn}')
        lines.append(f'    auto_accept_shared_attachments  = "{options.get("AutoAcceptSharedAttachments", "disable")}"')
        lines.append(f'    default_route_table_association = "{options.get("DefaultRouteTableAssociation", "disable")}"')
        lines.append(f'    default_route_table_propagation = "{options.get("DefaultRouteTablePropagation", "disable")}"')
        lines.append(f'    dns_support                     = "{options.get("DnsSupport", "enable")}"')
        lines.append(f'    vpn_ecmp_support                = "{options.get("VpnEcmpSupport", "enable")}"')
        lines.append("  }")
        lines.append("")

        # Collect VPC attachments for the selected TGW
        tgw_attachments_data = self.load_json('tgw-attachments.json')
        vpc_attachments = {}
        peering_attachments = {}
        vpn_attachments = {}
        dx_gateway_attachments = {}

        for attachment in tgw_attachments_data.get('TransitGatewayAttachments', []):
            # Only include attachments for the selected TGW
            if attachment.get('TransitGatewayId') != self.selected_tgw_id:
                continue

            attachment_id = attachment['TransitGatewayAttachmentId']
            resource_type = attachment.get('ResourceType', '')
            name = self.get_tag_value(attachment.get('Tags'), 'Name', attachment_id)
            key = self.sanitize_key(name)

            if resource_type == 'vpc':
                vpc_id = attachment.get('ResourceId', '')
                subnet_ids = []
                vpc_att_file = self.input_dir / f'tgw-vpc-attachment-{attachment_id}.json'
                if vpc_att_file.exists():
                    with open(vpc_att_file, 'r', encoding='utf-8') as f:
                        vpc_att_detail = json.load(f)
                        vpc_att = vpc_att_detail.get('TransitGatewayVpcAttachments', [])
                        if vpc_att:
                            subnet_ids = vpc_att[0].get('SubnetIds', [])

                vpc_attachments[key] = {
                    'name': name,
                    'vpc_id': vpc_id,
                    'subnet_ids': subnet_ids,
                    'attachment_id': attachment_id
                }

            elif resource_type == 'peering':
                peer_att_file = self.input_dir / f'tgw-peering-attachment-{attachment_id}.json'
                peer_tgw_id = ''
                peer_region = ''
                peer_account_id = ''
                if peer_att_file.exists():
                    with open(peer_att_file, 'r', encoding='utf-8') as f:
                        peer_att_detail = json.load(f)
                        peer_att = peer_att_detail.get('TransitGatewayPeeringAttachments', [])
                        if peer_att:
                            peering = peer_att[0]
                            peer_tgw_id = peering.get('AccepterTgwInfo', {}).get('TransitGatewayId', '')
                            peer_region = peering.get('AccepterTgwInfo', {}).get('Region', '')
                            peer_account_id = peering.get('AccepterTgwInfo', {}).get('OwnerId', '')

                peering_attachments[key] = {
                    'name': name,
                    'peer_transit_gateway_id': peer_tgw_id,
                    'peer_region': peer_region,
                    'peer_account_id': peer_account_id,
                    'attachment_id': attachment_id
                }

            elif resource_type == 'vpn':
                vpn_attachments[key] = {
                    'name': name,
                    'attachment_id': attachment_id,
                    'vpn_connection_id': attachment.get('ResourceId', '')
                }

            elif resource_type == 'direct-connect-gateway':
                dx_gateway_attachments[key] = {
                    'name': name,
                    'attachment_id': attachment_id,
                    'dx_gateway_id': attachment.get('ResourceId', '')
                }

        # Add VPC Attachments
        lines.append("  # VPC Attachments")
        lines.append("  vpc_attachments = {")
        for key, att in vpc_attachments.items():
            lines.append(f'    {key} = {{')
            lines.append(f'      name       = "{att["name"]}"')
            lines.append(f'      vpc_id     = "{att["vpc_id"]}"')
            lines.append(f'      subnet_ids = {json.dumps(att["subnet_ids"])}')
            lines.append('    }')
        lines.append("  }")
        lines.append("")

        # Add Peering Attachments
        lines.append("  # Peering Attachments")
        lines.append("  peering_attachments = {")
        for key, att in peering_attachments.items():
            lines.append(f'    {key} = {{')
            lines.append(f'      name                    = "{att["name"]}"')
            lines.append(f'      peer_transit_gateway_id = "{att["peer_transit_gateway_id"]}"')
            lines.append(f'      peer_region             = "{att["peer_region"]}"')
            if att.get('peer_account_id'):
                lines.append(f'      peer_account_id         = "{att["peer_account_id"]}"')
            lines.append('    }')
        lines.append("  }")
        lines.append("")

        # Add VPN Attachments
        lines.append("  # VPN Attachments (read-only via data source)")
        lines.append("  # These are managed outside Terraform - use data source to reference them")
        lines.append("  vpn_attachments = {")
        for key, att in vpn_attachments.items():
            lines.append(f'    {key} = {{')
            lines.append(f'      name              = "{att["name"]}"')
            lines.append(f'      attachment_id     = "{att["attachment_id"]}"')
            lines.append(f'      vpn_connection_id = "{att["vpn_connection_id"]}"')
            lines.append('    }')
        lines.append("  }")
        lines.append("")

        # Add Direct Connect Gateway Attachments
        lines.append("  # Direct Connect Gateway Attachments (read-only via data source)")
        lines.append("  # These are managed outside Terraform - use data source to reference them")
        lines.append("  dx_gateway_attachments = {")
        for key, att in dx_gateway_attachments.items():
            lines.append(f'    {key} = {{')
            lines.append(f'      name          = "{att["name"]}"')
            lines.append(f'      attachment_id = "{att["attachment_id"]}"')
            lines.append(f'      dx_gateway_id = "{att["dx_gateway_id"]}"')
            lines.append('    }')
        lines.append("  }")
        lines.append("")

        lines.append("  # Common tags")
        lines.append("  tags = {")
        lines.append('    ManagedBy   = "Terraform"')
        lines.append('    Project     = "TransitGateway"')
        lines.append('    Environment = local.environment')
        lines.append("  }")
        lines.append("}")
        lines.append("")

        return '\n'.join(lines)

    def generate_route_table_locals(self, rt_id: str, rt_name: str,
                                     rt_tags: dict,
                                     attachments_data: Dict[str, Any],
                                     associations: List[Tuple[str, str, str]],
                                     propagations: List[Tuple[str, str, str]],
                                     routes: List[Dict[str, Any]]) -> str:
        """Generate locals.tf content for a route table."""
        lines = ["# Route Table Configuration"]
        lines.append("# This file defines all resources associated with this specific route table")
        lines.append("")
        lines.append("locals {")
        lines.append(f'  route_table_name = "{rt_name}"')
        lines.append("")

        # Note: VPC and Peering Attachments are managed in the tgw/ directory
        # Route tables only define associations and reference attachments from tgw module

        # Associations
        lines.append("  # Route Table Associations")
        lines.append("  associations = {")
        for assoc_key, att_key, att_type in associations:
            lines.append(f'    {assoc_key} = {{')
            lines.append(f'      attachment_key  = "{att_key}"')
            lines.append(f'      attachment_type = "{att_type}"')
            lines.append('    }')
        lines.append("  }")
        lines.append("")

        # Propagations
        lines.append("  # Route Table Propagations")
        lines.append("  propagations = {")
        for prop_key, att_key, att_type in propagations:
            lines.append(f'    {prop_key} = {{')
            lines.append(f'      attachment_key  = "{att_key}"')
            lines.append(f'      attachment_type = "{att_type}"')
            lines.append('    }')
        lines.append("  }")
        lines.append("")

        # TGW Routes
        lines.append("  # Transit Gateway Routes")
        lines.append("  tgw_routes = {")
        for route in routes:
            route_key = route['key']
            lines.append(f'    {route_key} = {{')
            lines.append(f'      destination_cidr_block = "{route["destination_cidr_block"]}"')
            if route.get('attachment_key'):
                lines.append(f'      attachment_key         = "{route["attachment_key"]}"')
                lines.append(f'      attachment_type        = "{route["attachment_type"]}"')
            if route.get('blackhole'):
                lines.append('      blackhole              = true')
            lines.append('    }')
        lines.append("  }")
        lines.append("")

        # Tags
        lines.append("  # Tags specific to this route table")
        if rt_tags:
            lines.append(f'  route_table_tags = {json.dumps(rt_tags)}')
        else:
            lines.append('  route_table_tags = {}')
        lines.append("}")
        lines.append("")

        return '\n'.join(lines)

    def collect_all_attachments(self) -> Dict[str, Any]:
        """Collect all attachment information indexed by attachment_id."""
        attachments = {}

        # Load all data
        tgw_attachments_data = self.load_json('tgw-attachments.json')

        for attachment in tgw_attachments_data.get('TransitGatewayAttachments', []):
            attachment_id = attachment['TransitGatewayAttachmentId']
            resource_type = attachment.get('ResourceType', '')
            name = self.get_tag_value(attachment.get('Tags'), 'Name', attachment_id)
            key = self.sanitize_key(name)

            attachments[attachment_id] = {
                'key': key,
                'type': resource_type,
                'name': name,
                'tags': {tag['Key']: tag['Value'] for tag in attachment.get('Tags', []) if 'Key' in tag},
                'attachment_id': attachment_id
            }

            if resource_type == 'vpc':
                vpc_id = attachment.get('ResourceId', '')
                subnet_ids = []
                vpc_att_file = self.input_dir / f'tgw-vpc-attachment-{attachment_id}.json'
                if vpc_att_file.exists():
                    with open(vpc_att_file, 'r', encoding='utf-8') as f:
                        vpc_att_detail = json.load(f)
                        vpc_att = vpc_att_detail.get('TransitGatewayVpcAttachments', [])
                        if vpc_att:
                            subnet_ids = vpc_att[0].get('SubnetIds', [])

                attachments[attachment_id].update({
                    'vpc_id': vpc_id,
                    'subnet_ids': subnet_ids,
                    'appliance_mode_support': attachment.get('Options', {}).get('ApplianceModeSupport', 'disable'),
                    'dns_support': attachment.get('Options', {}).get('DnsSupport', 'enable'),
                    'ipv6_support': attachment.get('Options', {}).get('Ipv6Support', 'disable'),
                })

            elif resource_type == 'peering':
                peer_att_file = self.input_dir / f'tgw-peering-attachment-{attachment_id}.json'
                if peer_att_file.exists():
                    with open(peer_att_file, 'r', encoding='utf-8') as f:
                        peer_att_detail = json.load(f)
                        peer_att = peer_att_detail.get('TransitGatewayPeeringAttachments', [])
                        if peer_att:
                            peering = peer_att[0]
                            attachments[attachment_id].update({
                                'peer_transit_gateway_id': peering.get('AccepterTgwInfo', {}).get('TransitGatewayId', ''),
                                'peer_region': peering.get('AccepterTgwInfo', {}).get('Region', ''),
                                'peer_account_id': peering.get('AccepterTgwInfo', {}).get('OwnerId', ''),
                            })

            elif resource_type == 'vpn':
                vpn_conn_id = attachment.get('ResourceId', '')
                vpn_att_file = self.input_dir / f'tgw-vpn-attachment-{attachment_id}.json'
                if vpn_att_file.exists():
                    with open(vpn_att_file, 'r', encoding='utf-8') as f:
                        vpn_detail = json.load(f)
                        vpn_conns = vpn_detail.get('VpnConnections', [])
                        if vpn_conns:
                            vpn = vpn_conns[0]
                            attachments[attachment_id].update({
                                'customer_gateway_id': vpn.get('CustomerGatewayId', ''),
                                'type': vpn.get('Type', 'ipsec.1'),
                                'static_routes_only': vpn.get('Options', {}).get('StaticRoutesOnly', False),
                            })

            elif resource_type == 'direct-connect-gateway':
                dx_gw_id = attachment.get('ResourceId', '')
                dx_att_file = self.input_dir / f'tgw-dx-attachment-{attachment_id}.json'
                dx_gw_data = None
                if dx_att_file.exists():
                    with open(dx_att_file, 'r', encoding='utf-8') as f:
                        dx_gw_data = json.load(f)

                allowed_prefixes = []
                # Note: allowed_prefixes might need to be extracted differently
                # depending on how AWS API returns this data

                attachments[attachment_id].update({
                    'dx_gateway_id': dx_gw_id,
                    'allowed_prefixes': allowed_prefixes,
                })

        return attachments

    def generate_all_configs(self) -> None:
        """Generate all configuration files."""
        # Generate tgw/locals.tf
        tgw_dir = self.output_dir / 'tgw'
        tgw_dir.mkdir(parents=True, exist_ok=True)

        tgw_locals = self.generate_shared_locals()
        (tgw_dir / 'locals.tf').write_text(tgw_locals, encoding='utf-8')
        print(f"✓ Generated: {tgw_dir / 'locals.tf'}")

        # Write static files for tgw directory
        tgw_versions = """terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }

  # Uncomment and configure for remote state storage
  # backend "s3" {
  #   bucket = "my-terraform-state"
  #   key    = "tgw/{account_id}/{region}/tgw/terraform.tfstate"
  #   region = "ap-northeast-1"
  # }
}

provider "aws" {
  region = local.region
}
"""

        tgw_main = MAIN_TF_TGW

        tgw_outputs = """# Output Transit Gateway ID and attachment IDs for use by route table directories
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
  description = "Map of peering attachment keys to IDs"
  value       = { for k, v in aws_ec2_transit_gateway_peering_attachment.this : k => v.id }
}

output "vpn_attachment_ids" {
  description = "Map of VPN attachment keys to attachment IDs (from data source)"
  value       = { for k, v in data.aws_ec2_transit_gateway_attachment.vpn : k => v.id }
}

output "dx_gateway_attachment_ids" {
  description = "Map of DX Gateway attachment keys to attachment IDs (from data source)"
  value       = { for k, v in data.aws_ec2_transit_gateway_attachment.dx_gateway : k => v.id }
}
"""

        (tgw_dir / 'versions.tf').write_text(tgw_versions, encoding='utf-8')
        (tgw_dir / 'main.tf').write_text(tgw_main, encoding='utf-8')
        (tgw_dir / 'outputs.tf').write_text(tgw_outputs, encoding='utf-8')
        print(f"✓ Generated: {tgw_dir / 'versions.tf'}")
        print(f"✓ Generated: {tgw_dir / 'main.tf'}")
        print(f"✓ Generated: {tgw_dir / 'outputs.tf'}")

        # Load route tables
        tgw_rts_data = self.load_json('tgw-route-tables.json')
        route_tables_data = self.load_json('route-tables.json')

        # Collect all attachments
        all_attachments = self.collect_all_attachments()

        # Process each route table
        for rt in tgw_rts_data.get('TransitGatewayRouteTables', []):
            rt_id = rt['TransitGatewayRouteTableId']
            rt_tgw_id = rt.get('TransitGatewayId')

            # Skip route tables not belonging to selected TGW
            if self.selected_tgw_id and rt_tgw_id != self.selected_tgw_id:
                continue

            rt_name = self.get_tag_value(rt.get('Tags'), 'Name', rt_id)
            rt_tags = {tag['Key']: tag['Value'] for tag in rt.get('Tags', []) if 'Key' in tag}

            # Create route table directory
            rt_dirname = self.sanitize_dirname(rt_name)
            rt_dir = self.output_dir / f'rt-{rt_dirname}'
            rt_dir.mkdir(parents=True, exist_ok=True)

            # Write static files
            (rt_dir / 'versions.tf').write_text(VERSIONS_TF, encoding='utf-8')
            (rt_dir / 'data.tf').write_text(DATA_TF, encoding='utf-8')
            (rt_dir / 'main.tf').write_text(MAIN_TF_RT, encoding='utf-8')

            # Collect associations
            associations = []
            assoc_file = self.input_dir / f'tgw-rt-associations-{rt_id}.json'
            if assoc_file.exists():
                with open(assoc_file, 'r', encoding='utf-8') as f:
                    assoc_data = json.load(f)
                    for assoc in assoc_data.get('Associations', []):
                        if assoc.get('State') != 'associated':
                            continue
                        att_id = assoc.get('TransitGatewayAttachmentId')
                        if att_id in all_attachments:
                            att = all_attachments[att_id]
                            associations.append((att['key'], att['key'], att['type']))

            # Collect propagations
            propagations = []
            prop_file = self.input_dir / f'tgw-rt-propagations-{rt_id}.json'
            if prop_file.exists():
                with open(prop_file, 'r', encoding='utf-8') as f:
                    prop_data = json.load(f)
                    for prop in prop_data.get('TransitGatewayRouteTablePropagations', []):
                        if prop.get('State') != 'enabled':
                            continue
                        att_id = prop.get('TransitGatewayAttachmentId')
                        if att_id in all_attachments:
                            att = all_attachments[att_id]
                            propagations.append((att['key'], att['key'], att['type']))

            # Collect routes
            routes = []
            routes_file = self.input_dir / f'tgw-rt-routes-{rt_id}.json'
            if routes_file.exists():
                with open(routes_file, encoding='utf-8') as f:
                    routes_data = json.load(f)
                    for route in routes_data.get('Routes', []):
                        if route.get('Type') == 'propagated':
                            continue
                        dest_cidr = route.get('DestinationCidrBlock', '')
                        if not dest_cidr:
                            continue

                        dest_sanitized = dest_cidr.replace('/', '_').replace('.', '_').replace(':', '_')
                        route_key = f'route_{dest_sanitized}'

                        is_blackhole = route.get('State') == 'blackhole'

                        route_entry = {
                            'key': route_key,
                            'destination_cidr_block': dest_cidr,
                            'blackhole': is_blackhole
                        }

                        if not is_blackhole:
                            # Find attachment
                            for att_info in route.get('TransitGatewayAttachments', []):
                                att_id = att_info.get('TransitGatewayAttachmentId')
                                if att_id in all_attachments:
                                    att = all_attachments[att_id]
                                    route_entry['attachment_key'] = att['key']
                                    route_entry['attachment_type'] = att['type']
                                    break

                        routes.append(route_entry)

            # Collect attachments for this route table
            rt_attachments = {}

            # Add attachments from associations
            for assoc_key, att_key, att_type in associations:
                for att_id, att in all_attachments.items():
                    if att['key'] == att_key:
                        rt_attachments[att_key] = att
                        break

            # Add attachments from propagations
            for prop_key, att_key, att_type in propagations:
                for att_id, att in all_attachments.items():
                    if att['key'] == att_key and att_key not in rt_attachments:
                        rt_attachments[att_key] = att
                        break

            # Add attachments from routes
            for route in routes:
                if 'attachment_key' in route:
                    att_key = route['attachment_key']
                    for att_id, att in all_attachments.items():
                        if att['key'] == att_key and att_key not in rt_attachments:
                            rt_attachments[att_key] = att
                            break

            # Generate locals.tf
            locals_content = self.generate_route_table_locals(
                rt_id, rt_name, rt_tags,
                rt_attachments,
                associations, propagations,
                routes
            )
            (rt_dir / 'locals.tf').write_text(locals_content, encoding='utf-8')
            print(f"✓ Generated: {rt_dir / 'locals.tf'}")

        print(f"\n✓ All configurations generated in: {self.output_dir}")
        print("\nNext steps:")
        print("1. Review and adjust the generated configurations")
        print("2. cd terraform/tgw && terraform init")
        print("3. terraform import aws_ec2_transit_gateway.this <tgw-id>")
        print("4. terraform apply")
        print("5. For each route table directory:")
        print("   cd terraform/rt-<name> && terraform init")
        print("   Run appropriate import commands")
        print("   terraform plan && terraform apply")


def main():
    """Main entry point."""
    import argparse
    import os

    parser = argparse.ArgumentParser(
        description='Generate split Terraform configuration from existing AWS resources'
    )
    parser.add_argument(
        '--input-dir',
        default=DEFAULT_INPUT_DIR,
        help=f'Directory containing AWS resource JSON files (default: {DEFAULT_INPUT_DIR})'
    )
    parser.add_argument(
        '--output-dir',
        default=DEFAULT_OUTPUT_DIR,
        help=f'Output directory for Terraform configuration (default: {DEFAULT_OUTPUT_DIR})'
    )
    parser.add_argument(
        '--account-id',
        default=None,
        help='AWS Account ID (auto-detected from input path if not specified)'
    )
    parser.add_argument(
        '--region',
        default=None,
        help='AWS Region (auto-detected from input path if not specified)'
    )

    args = parser.parse_args()

    # Auto-detect account and region from input directory structure
    # Expected: ./output/{account_id}/{region}/
    account_id = args.account_id
    region = args.region

    if not account_id or not region:
        input_path = Path(args.input_dir)
        parts = input_path.parts
        if len(parts) >= 2:
            # Check if last two parts look like account_id/region
            potential_region = parts[-1]
            potential_account = parts[-2]

            if not region and potential_region:
                region = potential_region
            if not account_id and potential_account and potential_account.isdigit():
                account_id = potential_account

    generator = TerraformConfigGeneratorV2(args.input_dir, args.output_dir, account_id, region)
    generator.generate_all_configs()


if __name__ == '__main__':
    main()
