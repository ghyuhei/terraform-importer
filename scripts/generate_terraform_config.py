#!/usr/bin/env python3
"""Terraform Configuration Generator for for_each-based module structure.

Generates terraform.tfvars configuration from existing AWS resources.
Works with the new for_each-based dynamic resource structure.

Requirements: Python 3.8+
"""

import json
from pathlib import Path
from typing import Dict, List, Any

# Constants
DEFAULT_INPUT_DIR = './output'
DEFAULT_OUTPUT_FILE = './terraform/terraform.tfvars'


class TerraformConfigGenerator:
    """Generator for Terraform configuration."""

    def __init__(self, input_dir: str) -> None:
        self.input_dir = Path(input_dir)

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

    def tags_to_map(self, tags: List[dict] | None) -> Dict[str, str]:
        """Convert AWS tags list to map."""
        if not tags:
            return {}
        return {tag['Key']: tag['Value'] for tag in tags if 'Key' in tag and 'Value' in tag}

    def sanitize_key(self, name: str) -> str:
        """Sanitize resource name for use as Terraform map key."""
        return name.replace('-', '_').replace(' ', '_').lower()

    def format_map(self, data: Dict[str, Any], indent: int = 0) -> str:
        """Format a dictionary as HCL map."""
        lines = []
        indent_str = "  " * indent

        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f'{indent_str}{key} = {{')
                lines.append(self.format_map(value, indent + 1))
                lines.append(f'{indent_str}}}')
            elif isinstance(value, list):
                lines.append(f'{indent_str}{key} = {json.dumps(value)}')
            elif isinstance(value, bool):
                lines.append(f'{indent_str}{key} = {str(value).lower()}')
            elif isinstance(value, (int, float)):
                lines.append(f'{indent_str}{key} = {value}')
            else:
                lines.append(f'{indent_str}{key} = "{value}"')

        return '\n'.join(lines)

    def generate_config(self) -> str:
        """Generate terraform.tfvars configuration."""
        lines = []
        lines.append("# Terraform Configuration")
        lines.append("# Auto-generated from existing AWS resources")
        lines.append("")

        # Load all data
        tgws_data = self.load_json('transit-gateways.json')
        tgw_rts_data = self.load_json('tgw-route-tables.json')
        tgw_attachments_data = self.load_json('tgw-attachments.json')
        route_tables_data = self.load_json('route-tables.json')

        # Extract region from TGW ARN if available
        region = "ap-northeast-1"  # default
        tgws = tgws_data.get('TransitGateways', [])
        if tgws:
            tgw_arn = tgws[0].get('OwnerId', '')
            if 'arn:aws' in str(tgws[0]):
                # Parse region from ARN if present
                pass

        # AWS Configuration
        lines.append("# =============================================================================")
        lines.append("# AWS Configuration")
        lines.append("# =============================================================================")
        lines.append("")
        lines.append(f'region      = "{region}"')
        lines.append('environment = "production"')
        lines.append("")

        # Transit Gateway Configuration
        if tgws:
            tgw = tgws[0]
            lines.append("# =============================================================================")
            lines.append("# Transit Gateway Configuration")
            lines.append("# =============================================================================")
            lines.append("")

            tgw_name = self.get_tag_value(tgw.get('Tags'), 'Name', 'tgw')
            tgw_desc = tgw.get('Options', {}).get('Description', 'Transit Gateway')
            tgw_asn = tgw.get('Options', {}).get('AmazonSideAsn', 64512)

            lines.append(f'transit_gateway_name        = "{tgw_name}"')
            lines.append(f'transit_gateway_description = "{tgw_desc}"')
            lines.append(f'transit_gateway_amazon_side_asn = {tgw_asn}')
            lines.append("")

            options = tgw.get('Options', {})
            lines.append(f'transit_gateway_auto_accept_shared_attachments = "{options.get("AutoAcceptSharedAttachments", "disable")}"')
            lines.append(f'transit_gateway_default_route_table_association = "{options.get("DefaultRouteTableAssociation", "disable")}"')
            lines.append(f'transit_gateway_default_route_table_propagation = "{options.get("DefaultRouteTablePropagation", "disable")}"')
            lines.append(f'transit_gateway_dns_support = "{options.get("DnsSupport", "enable")}"')
            lines.append(f'transit_gateway_vpn_ecmp_support = "{options.get("VpnEcmpSupport", "enable")}"')
            lines.append("")

        # Route Tables
        route_tables = {}
        rt_id_to_key = {}

        for rt in tgw_rts_data.get('TransitGatewayRouteTables', []):
            rt_id = rt['TransitGatewayRouteTableId']
            name = self.get_tag_value(rt.get('Tags'), 'Name', rt_id)
            key = self.sanitize_key(name)
            rt_id_to_key[rt_id] = key

            route_tables[key] = {
                'name': name,
                'tags': self.tags_to_map(rt.get('Tags'))
            }

        if route_tables:
            lines.append("# =============================================================================")
            lines.append("# Transit Gateway Route Tables")
            lines.append("# =============================================================================")
            lines.append("")
            lines.append("route_tables = {")
            for key, config in route_tables.items():
                lines.append(f'  {key} = {{')
                lines.append(f'    name = "{config["name"]}"')
                if config['tags']:
                    lines.append('    tags = {')
                    for tag_key, tag_value in config['tags'].items():
                        lines.append(f'      "{tag_key}" = "{tag_value}"')
                    lines.append('    }')
                lines.append('  }')
            lines.append("}")
            lines.append("")

        # VPC Attachments
        vpc_attachments = {}
        attachment_id_to_key = {}  # Maps attachment_id -> (key, type)

        for attachment in tgw_attachments_data.get('TransitGatewayAttachments', []):
            if attachment.get('ResourceType') != 'vpc':
                continue

            attachment_id = attachment['TransitGatewayAttachmentId']
            name = self.get_tag_value(attachment.get('Tags'), 'Name', attachment_id)
            key = self.sanitize_key(name)
            attachment_id_to_key[attachment_id] = (key, 'vpc')

            vpc_id = attachment.get('ResourceId', '')

            # Try to get subnet_ids from detailed VPC attachment file
            subnet_ids = []
            vpc_att_detail_file = self.input_dir / f'tgw-vpc-attachment-{attachment_id}.json'
            if vpc_att_detail_file.exists():
                with open(vpc_att_detail_file, 'r', encoding='utf-8') as f:
                    vpc_att_detail = json.load(f)
                    vpc_att = vpc_att_detail.get('TransitGatewayVpcAttachments', [])
                    if vpc_att:
                        subnet_ids = vpc_att[0].get('SubnetIds', [])

            vpc_attachments[key] = {
                'name': name,
                'vpc_id': vpc_id,
                'subnet_ids': subnet_ids,
                'appliance_mode_support': attachment.get('Options', {}).get('ApplianceModeSupport', 'disable'),
                'dns_support': attachment.get('Options', {}).get('DnsSupport', 'enable'),
                'ipv6_support': attachment.get('Options', {}).get('Ipv6Support', 'disable'),
                'tags': self.tags_to_map(attachment.get('Tags'))
            }

        if vpc_attachments:
            lines.append("# =============================================================================")
            lines.append("# VPC Attachments")
            lines.append("# =============================================================================")
            lines.append("")
            lines.append("vpc_attachments = {")
            for key, config in vpc_attachments.items():
                lines.append(f'  {key} = {{')
                lines.append(f'    name       = "{config["name"]}"')
                lines.append(f'    vpc_id     = "{config["vpc_id"]}"')
                lines.append(f'    subnet_ids = {json.dumps(config["subnet_ids"])}')
                if config['appliance_mode_support'] != 'disable':
                    lines.append(f'    appliance_mode_support = "{config["appliance_mode_support"]}"')
                if config['dns_support'] != 'enable':
                    lines.append(f'    dns_support = "{config["dns_support"]}"')
                if config['ipv6_support'] != 'disable':
                    lines.append(f'    ipv6_support = "{config["ipv6_support"]}"')
                if config['tags']:
                    lines.append('    tags = {')
                    for tag_key, tag_value in config['tags'].items():
                        lines.append(f'      "{tag_key}" = "{tag_value}"')
                    lines.append('    }')
                lines.append('  }')
            lines.append("}")
            lines.append("")

        # Peering Attachments
        peering_attachments = {}
        for attachment in tgw_attachments_data.get('TransitGatewayAttachments', []):
            if attachment.get('ResourceType') != 'peering':
                continue

            attachment_id = attachment['TransitGatewayAttachmentId']
            name = self.get_tag_value(attachment.get('Tags'), 'Name', attachment_id)
            key = self.sanitize_key(name)
            attachment_id_to_key[attachment_id] = (key, 'peering')

            # Get detailed peering attachment information
            peer_tgw_id = ""
            peer_region = ""
            peer_account_id = ""

            peer_att_detail_file = self.input_dir / f'tgw-peering-attachment-{attachment_id}.json'
            if peer_att_detail_file.exists():
                with open(peer_att_detail_file, 'r', encoding='utf-8') as f:
                    peer_att_detail = json.load(f)
                    peer_att = peer_att_detail.get('TransitGatewayPeeringAttachments', [])
                    if peer_att:
                        peering = peer_att[0]
                        peer_tgw_id = peering.get('AccepterTgwInfo', {}).get('TransitGatewayId', '')
                        peer_region = peering.get('AccepterTgwInfo', {}).get('Region', '')
                        peer_account_id = peering.get('AccepterTgwInfo', {}).get('OwnerId', '')

            if peer_tgw_id and peer_region:
                peering_attachments[key] = {
                    'name': name,
                    'peer_transit_gateway_id': peer_tgw_id,
                    'peer_region': peer_region,
                    'peer_account_id': peer_account_id,
                    'tags': self.tags_to_map(attachment.get('Tags'))
                }

        if peering_attachments:
            lines.append("# =============================================================================")
            lines.append("# Peering Attachments (Inter-region TGW Peering)")
            lines.append("# =============================================================================")
            lines.append("")
            lines.append("peering_attachments = {")
            for key, config in peering_attachments.items():
                lines.append(f'  {key} = {{')
                lines.append(f'    name                    = "{config["name"]}"')
                lines.append(f'    peer_transit_gateway_id = "{config["peer_transit_gateway_id"]}"')
                lines.append(f'    peer_region             = "{config["peer_region"]}"')
                if config['peer_account_id']:
                    lines.append(f'    peer_account_id         = "{config["peer_account_id"]}"')
                if config['tags']:
                    lines.append('    tags = {')
                    for tag_key, tag_value in config['tags'].items():
                        lines.append(f'      "{tag_key}" = "{tag_value}"')
                    lines.append('    }')
                lines.append('  }')
            lines.append("}")
            lines.append("")

        # Route Table Associations
        associations = {}
        for rt_id, rt_key in rt_id_to_key.items():
            assoc_file = self.input_dir / f'tgw-rt-associations-{rt_id}.json'
            if not assoc_file.exists():
                continue

            with open(assoc_file, 'r', encoding='utf-8') as f:
                assoc_data = json.load(f)

            for assoc in assoc_data.get('Associations', []):
                if assoc.get('State') != 'associated':
                    continue

                attachment_id = assoc.get('TransitGatewayAttachmentId')
                if attachment_id not in attachment_id_to_key:
                    continue

                attachment_key, attachment_type = attachment_id_to_key[attachment_id]
                assoc_key = f"{rt_key}_{attachment_key}"

                associations[assoc_key] = {
                    'route_table_key': rt_key,
                    'attachment_key': attachment_key,
                    'attachment_type': attachment_type
                }

        if associations:
            lines.append("# =============================================================================")
            lines.append("# Route Table Associations")
            lines.append("# =============================================================================")
            lines.append("")
            lines.append("route_table_associations = {")
            for key, config in associations.items():
                lines.append(f'  {key} = {{')
                lines.append(f'    route_table_key = "{config["route_table_key"]}"')
                lines.append(f'    attachment_key  = "{config["attachment_key"]}"')
                if config.get('attachment_type') != 'vpc':
                    lines.append(f'    attachment_type = "{config["attachment_type"]}"')
                lines.append('  }')
            lines.append("}")
            lines.append("")

        # Route Table Propagations
        propagations = {}
        for rt_id, rt_key in rt_id_to_key.items():
            prop_file = self.input_dir / f'tgw-rt-propagations-{rt_id}.json'
            if not prop_file.exists():
                continue

            with open(prop_file, 'r', encoding='utf-8') as f:
                prop_data = json.load(f)

            for prop in prop_data.get('TransitGatewayRouteTablePropagations', []):
                if prop.get('State') != 'enabled':
                    continue

                attachment_id = prop.get('TransitGatewayAttachmentId')
                if attachment_id not in attachment_id_to_key:
                    continue

                attachment_key, attachment_type = attachment_id_to_key[attachment_id]
                prop_key = f"{rt_key}_{attachment_key}"

                propagations[prop_key] = {
                    'route_table_key': rt_key,
                    'attachment_key': attachment_key,
                    'attachment_type': attachment_type
                }

        if propagations:
            lines.append("# =============================================================================")
            lines.append("# Route Table Propagations")
            lines.append("# =============================================================================")
            lines.append("")
            lines.append("route_table_propagations = {")
            for key, config in propagations.items():
                lines.append(f'  {key} = {{')
                lines.append(f'    route_table_key = "{config["route_table_key"]}"')
                lines.append(f'    attachment_key  = "{config["attachment_key"]}"')
                if config.get('attachment_type') != 'vpc':
                    lines.append(f'    attachment_type = "{config["attachment_type"]}"')
                lines.append('  }')
            lines.append("}")
            lines.append("")

        # Transit Gateway Routes
        tgw_routes = {}
        for rt_id, rt_key in rt_id_to_key.items():
            routes_file = self.input_dir / f'tgw-rt-routes-{rt_id}.json'
            if not routes_file.exists():
                continue

            with open(routes_file, encoding='utf-8') as f:
                routes_data = json.load(f)

            for route in routes_data.get('Routes', []):
                # Skip propagated routes
                if route.get('Type') == 'propagated':
                    continue

                dest_cidr = route.get('DestinationCidrBlock', '')
                if not dest_cidr:
                    continue

                dest_sanitized = dest_cidr.replace('/', '_').replace('.', '_')
                route_key = f"{rt_key}_{dest_sanitized}"

                is_blackhole = route.get('State') == 'blackhole'

                tgw_routes[route_key] = {
                    'destination_cidr_block': dest_cidr,
                    'route_table_key': rt_key,
                    'blackhole': is_blackhole
                }

                # Add attachment key if not blackhole
                if not is_blackhole:
                    # Find attachment from route
                    for attachment_id, (attachment_key, attachment_type) in attachment_id_to_key.items():
                        if attachment_id in str(route.get('TransitGatewayAttachments', [])):
                            tgw_routes[route_key]['attachment_key'] = attachment_key
                            tgw_routes[route_key]['attachment_type'] = attachment_type
                            break

        if tgw_routes:
            lines.append("# =============================================================================")
            lines.append("# Transit Gateway Routes")
            lines.append("# =============================================================================")
            lines.append("")
            lines.append("tgw_routes = {")
            for key, config in tgw_routes.items():
                lines.append(f'  {key} = {{')
                lines.append(f'    destination_cidr_block = "{config["destination_cidr_block"]}"')
                lines.append(f'    route_table_key        = "{config["route_table_key"]}"')
                if 'attachment_key' in config:
                    lines.append(f'    attachment_key         = "{config["attachment_key"]}"')
                if config.get('attachment_type') and config.get('attachment_type') != 'vpc':
                    lines.append(f'    attachment_type        = "{config["attachment_type"]}"')
                if config.get('blackhole'):
                    lines.append('    blackhole              = true')
                lines.append('  }')
            lines.append("}")
            lines.append("")

        # VPC Routes
        vpc_routes = {}
        for rt in route_tables_data.get('RouteTables', []):
            rt_id = rt['RouteTableId']
            name = self.get_tag_value(rt.get('Tags'), 'Name', rt_id)
            vpc_rt_key = self.sanitize_key(name)

            routes = rt.get('Routes', [])
            for route in routes:
                if 'TransitGatewayId' not in route:
                    continue

                destination = route.get('DestinationCidrBlock', route.get('DestinationIpv6CidrBlock', ''))
                if not destination or destination == 'local':
                    continue

                dest_sanitized = destination.replace('/', '_').replace('.', '_').replace(':', '_')
                route_key = f"{vpc_rt_key}_to_{dest_sanitized}"

                vpc_routes[route_key] = {
                    'route_table_id': rt_id,
                    'destination_cidr_block': destination
                }

        if vpc_routes:
            lines.append("# =============================================================================")
            lines.append("# VPC Routes to Transit Gateway")
            lines.append("# =============================================================================")
            lines.append("")
            lines.append("vpc_routes = {")
            for key, config in vpc_routes.items():
                lines.append(f'  {key} = {{')
                lines.append(f'    route_table_id         = "{config["route_table_id"]}"')
                lines.append(f'    destination_cidr_block = "{config["destination_cidr_block"]}"')
                lines.append('  }')
            lines.append("}")
            lines.append("")

        # Tags
        lines.append("# =============================================================================")
        lines.append("# Common Tags")
        lines.append("# =============================================================================")
        lines.append("")
        lines.append("tags = {")
        lines.append('  ManagedBy = "Terraform"')
        lines.append('  Project   = "TransitGateway"')
        lines.append("}")
        lines.append("")

        return '\n'.join(lines)

    def generate_to_file(self, output_file: str) -> None:
        """Generate configuration and save to file."""
        config = self.generate_config()

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(config)

        print(f"✓ Generated Terraform configuration: {output_path.absolute()}")
        print(f"  Review and adjust the configuration before running terraform plan")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate Terraform configuration from existing AWS resources'
    )
    parser.add_argument(
        '--input-dir',
        default=DEFAULT_INPUT_DIR,
        help=f'Directory containing AWS resource JSON files (default: {DEFAULT_INPUT_DIR})'
    )
    parser.add_argument(
        '--output',
        default=DEFAULT_OUTPUT_FILE,
        help=f'Output file for Terraform configuration (default: {DEFAULT_OUTPUT_FILE})'
    )

    args = parser.parse_args()

    generator = TerraformConfigGenerator(args.input_dir)
    generator.generate_to_file(args.output)


if __name__ == '__main__':
    main()
