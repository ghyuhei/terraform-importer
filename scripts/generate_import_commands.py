#!/usr/bin/env python3
"""Terraform Import Command Generator for for_each-based module structure.

Generates terraform import commands for resources managed by the transit-gateway module.
Works with the new for_each-based dynamic resource structure.

Requirements: Python 3.8+
"""

import json
import os
from pathlib import Path
from typing import Dict, List

# Constants
DEFAULT_INPUT_DIR = './output'
DEFAULT_OUTPUT_FILE = './terraform/import.sh'


class ImportCommandGenerator:
    """Generator for Terraform import commands."""

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

    def sanitize_key(self, name: str) -> str:
        """Sanitize resource name for use as Terraform map key."""
        # Convert to lowercase and replace special characters with underscores
        return name.replace('-', '_').replace(' ', '_').lower()

    def generate_import_commands(self) -> str:
        """Generate all import commands for for_each-based module."""
        commands = []
        commands.append("#!/bin/bash")
        commands.append("")
        commands.append("# Terraform Import Commands")
        commands.append("# Auto-generated script to import existing AWS resources into Terraform")
        commands.append("# This script works with the for_each-based transit-gateway module")
        commands.append("")
        commands.append("set -euo pipefail")
        commands.append("")
        commands.append('cd "$(dirname "$0")"')
        commands.append("")

        # Load all data
        tgws_data = self.load_json('transit-gateways.json')
        tgw_rts_data = self.load_json('tgw-route-tables.json')
        tgw_attachments_data = self.load_json('tgw-attachments.json')
        route_tables_data = self.load_json('route-tables.json')

        # Maps to track resource relationships
        rt_id_to_key = {}  # route table ID -> map key
        attachment_id_to_key = {}  # attachment ID -> map key

        # Import Transit Gateway (single resource, not for_each)
        commands.append("echo 'Importing Transit Gateway...'")
        tgws = tgws_data.get('TransitGateways', [])
        if tgws:
            tgw = tgws[0]  # Assume single TGW
            tgw_id = tgw['TransitGatewayId']
            name = self.get_tag_value(tgw.get('Tags', []), 'Name', tgw_id)

            commands.append(f"# Transit Gateway: {name}")
            commands.append(
                f"terraform import 'module.transit_gateway.aws_ec2_transit_gateway.this' {tgw_id}"
            )
            commands.append("")

        # Import Transit Gateway Route Tables (for_each)
        commands.append("echo 'Importing Transit Gateway Route Tables...'")
        for rt in tgw_rts_data.get('TransitGatewayRouteTables', []):
            rt_id = rt['TransitGatewayRouteTableId']
            name = self.get_tag_value(rt.get('Tags', []), 'Name', rt_id)
            key = self.sanitize_key(name)
            rt_id_to_key[rt_id] = key

            commands.append(f"# Route Table: {name} (key: {key})")
            commands.append(
                f'terraform import \'module.transit_gateway.aws_ec2_transit_gateway_route_table.this["{key}"]\' {rt_id}'
            )
            commands.append("")

        # Import Transit Gateway VPC Attachments (for_each)
        commands.append("echo 'Importing Transit Gateway VPC Attachments...'")
        for attachment in tgw_attachments_data.get('TransitGatewayAttachments', []):
            if attachment.get('ResourceType') != 'vpc':
                continue

            attachment_id = attachment['TransitGatewayAttachmentId']
            name = self.get_tag_value(attachment.get('Tags', []), 'Name', attachment_id)
            key = self.sanitize_key(name)
            attachment_id_to_key[attachment_id] = key

            commands.append(f"# VPC Attachment: {name} (key: {key})")
            commands.append(
                f'terraform import \'module.transit_gateway.aws_ec2_transit_gateway_vpc_attachment.this["{key}"]\' {attachment_id}'
            )
            commands.append("")

        # Import Route Table Associations (for_each)
        commands.append("echo 'Importing Route Table Associations...'")
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

                attachment_key = attachment_id_to_key[attachment_id]
                # Create a unique key for the association
                assoc_key = f"{rt_key}_{attachment_key}"

                commands.append(f"# Association: {rt_key} <-> {attachment_key} (key: {assoc_key})")
                commands.append(
                    f'terraform import \'module.transit_gateway.aws_ec2_transit_gateway_route_table_association.this["{assoc_key}"]\' '
                    f'{rt_id}_{attachment_id}'
                )
                commands.append("")

        # Import Route Table Propagations (for_each)
        commands.append("echo 'Importing Route Table Propagations...'")
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

                attachment_key = attachment_id_to_key[attachment_id]
                # Create a unique key for the propagation
                prop_key = f"{rt_key}_{attachment_key}"

                commands.append(f"# Propagation: {rt_key} <-> {attachment_key} (key: {prop_key})")
                commands.append(
                    f'terraform import \'module.transit_gateway.aws_ec2_transit_gateway_route_table_propagation.this["{prop_key}"]\' '
                    f'{rt_id}_{attachment_id}'
                )
                commands.append("")

        # Import Transit Gateway Routes (for_each)
        commands.append("echo 'Importing Transit Gateway Routes...'")
        for rt_id, rt_key in rt_id_to_key.items():
            routes_file = self.input_dir / f'tgw-rt-routes-{rt_id}.json'
            if not routes_file.exists():
                continue

            with open(routes_file, encoding='utf-8') as f:
                routes_data = json.load(f)

            for route in routes_data.get('Routes', []):
                # Skip propagated routes (only import static routes)
                if route.get('Type') == 'propagated':
                    continue

                dest_cidr = route.get('DestinationCidrBlock', '')
                if not dest_cidr:
                    continue

                # Create a unique key for the route
                dest_sanitized = dest_cidr.replace('/', '_').replace('.', '_')
                route_key = f"{rt_key}_{dest_sanitized}"

                # Check if it's a blackhole route
                is_blackhole = route.get('State') == 'blackhole'
                route_type = "blackhole" if is_blackhole else "attachment"

                commands.append(f"# TGW Route: {dest_cidr} in {rt_key} ({route_type}, key: {route_key})")
                commands.append(
                    f'terraform import \'module.transit_gateway.aws_ec2_transit_gateway_route.this["{route_key}"]\' '
                    f'{rt_id}_{dest_cidr}'
                )
                commands.append("")

        # Import VPC Routes (for_each)
        commands.append("echo 'Importing VPC Routes...'")
        for rt in route_tables_data.get('RouteTables', []):
            rt_id = rt['RouteTableId']
            name = self.get_tag_value(rt.get('Tags', []), 'Name', rt_id)
            rt_key = self.sanitize_key(name)

            routes = rt.get('Routes', [])
            for route in routes:
                # Only import routes that point to Transit Gateway
                if 'TransitGatewayId' not in route:
                    continue

                destination = route.get('DestinationCidrBlock', route.get('DestinationIpv6CidrBlock', ''))
                if not destination or destination == 'local':
                    continue

                dest_sanitized = destination.replace('/', '_').replace('.', '_').replace(':', '_')
                route_key = f"{rt_key}_to_{dest_sanitized}"

                commands.append(f"# VPC Route: {destination} via TGW in {name} (key: {route_key})")
                commands.append(
                    f'terraform import \'module.transit_gateway.aws_route.this["{route_key}"]\' {rt_id}_{destination}'
                )
                commands.append("")

        commands.append("echo 'Import completed!'")
        commands.append("echo 'Next steps:'")
        commands.append("echo '  1. Run terraform plan to verify the imported state'")
        commands.append("echo '  2. Review terraform.tfvars and adjust if needed to eliminate differences'")
        commands.append("")

        return '\n'.join(commands)

    def generate_to_file(self, output_file: str) -> None:
        """Generate import commands and save to file."""
        commands = self.generate_import_commands()

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(commands)

        # Make the script executable
        os.chmod(output_path, 0o755)

        print(f"✓ Generated import script: {output_path.absolute()}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate Terraform import commands for existing AWS resources'
    )
    parser.add_argument(
        '--input-dir',
        default=DEFAULT_INPUT_DIR,
        help=f'Directory containing AWS resource JSON files (default: {DEFAULT_INPUT_DIR})'
    )
    parser.add_argument(
        '--output',
        default=DEFAULT_OUTPUT_FILE,
        help=f'Output file for import commands (default: {DEFAULT_OUTPUT_FILE})'
    )

    args = parser.parse_args()

    generator = ImportCommandGenerator(args.input_dir)
    generator.generate_to_file(args.output)


if __name__ == '__main__':
    main()
