#!/usr/bin/env python3
"""Terraform Import Command Generator.

Generates terraform import commands for all resources
defined in the generated Terraform configuration files.

Requirements: Python 3.8+
"""

import json
import os
from pathlib import Path

# Constants
DEFAULT_INPUT_DIR = './output'
DEFAULT_TERRAFORM_DIR = './terraform'
DEFAULT_OUTPUT_FILE = './scripts/import.sh'


class ImportCommandGenerator:
    """Generator for Terraform import commands."""

    def __init__(self, input_dir: str, terraform_dir: str) -> None:
        self.input_dir = Path(input_dir)
        self.terraform_dir = Path(terraform_dir)

    def load_json(self, filename: str) -> dict:
        """Load JSON file from input directory."""
        filepath = self.input_dir / filename
        if not filepath.exists():
            return {}
        with open(filepath, encoding='utf-8') as f:
            return json.load(f)

    def get_tag_value(self, tags: list[dict] | None, key: str, default: str = "") -> str:
        """Extract tag value from AWS tags list."""
        if not tags:
            return default
        for tag in tags:
            if tag.get('Key') == key:
                return tag.get('Value', default)
        return default

    def sanitize_resource_name(self, name: str) -> str:
        """Sanitize resource name for Terraform."""
        return name.replace('-', '_').replace(' ', '_').lower()

    def generate_import_commands(self) -> str:
        """Generate all import commands."""
        commands = []
        commands.append("#!/bin/bash")
        commands.append("")
        commands.append("# Terraform Import Commands")
        commands.append("# Auto-generated script to import existing AWS resources into Terraform")
        commands.append("")
        commands.append("set -euo pipefail")
        commands.append("")
        commands.append(f'cd "{self.terraform_dir.resolve()}"')
        commands.append("")

        # Load all data
        tgws_data = self.load_json('transit-gateways.json')
        tgw_rts_data = self.load_json('tgw-route-tables.json')
        tgw_attachments_data = self.load_json('tgw-attachments.json')
        route_tables_data = self.load_json('route-tables.json')

        # Maps to track resource relationships
        tgw_resources = {}
        rt_resources = {}
        attachment_resources = {}

        # Import Transit Gateways
        commands.append("echo 'Importing Transit Gateways...'")
        for tgw in tgws_data.get('TransitGateways', []):
            tgw_id = tgw['TransitGatewayId']
            name = self.get_tag_value(tgw.get('Tags', []), 'Name', tgw_id)
            resource_name = self.sanitize_resource_name(name)
            tgw_resources[tgw_id] = resource_name

            commands.append(f"# Transit Gateway: {name}")
            commands.append(
                f'terraform import aws_ec2_transit_gateway.{resource_name} {tgw_id}'
            )
            commands.append("")

        # Import Transit Gateway Route Tables
        commands.append("echo 'Importing Transit Gateway Route Tables...'")
        for rt in tgw_rts_data.get('TransitGatewayRouteTables', []):
            rt_id = rt['TransitGatewayRouteTableId']
            tgw_id = rt['TransitGatewayId']

            if tgw_id not in tgw_resources:
                continue

            name = self.get_tag_value(rt.get('Tags', []), 'Name', rt_id)
            resource_name = self.sanitize_resource_name(name)
            rt_resources[rt_id] = resource_name

            commands.append(f"# Route Table: {name}")
            commands.append(
                f'terraform import aws_ec2_transit_gateway_route_table.{resource_name} {rt_id}'
            )
            commands.append("")

        # Import Transit Gateway VPC Attachments
        commands.append("echo 'Importing Transit Gateway VPC Attachments...'")
        for attachment in tgw_attachments_data.get('TransitGatewayAttachments', []):
            if attachment.get('ResourceType') != 'vpc':
                continue

            attachment_id = attachment['TransitGatewayAttachmentId']
            tgw_id = attachment['TransitGatewayId']

            if tgw_id not in tgw_resources:
                continue

            name = self.get_tag_value(attachment.get('Tags', []), 'Name', attachment_id)
            resource_name = self.sanitize_resource_name(name)
            attachment_resources[attachment_id] = resource_name

            commands.append(f"# VPC Attachment: {name}")
            commands.append(
                f'terraform import aws_ec2_transit_gateway_vpc_attachment.{resource_name} {attachment_id}'
            )
            commands.append("")

        # Import Route Table Associations
        commands.append("echo 'Importing Route Table Associations...'")
        for rt_id, rt_resource_name in rt_resources.items():
            assoc_file = self.input_dir / f'tgw-rt-associations-{rt_id}.json'
            if not assoc_file.exists():
                continue

            with open(assoc_file, 'r', encoding='utf-8') as f:
                assoc_data = json.load(f)

            for assoc in assoc_data.get('Associations', []):
                attachment_id = assoc.get('TransitGatewayAttachmentId')

                if attachment_id not in attachment_resources:
                    continue

                attachment_resource_name = attachment_resources[attachment_id]
                resource_name = f"{rt_resource_name}_assoc_{attachment_resource_name}"

                commands.append(f"# Association: {rt_id} <-> {attachment_id}")
                commands.append(
                    f'terraform import aws_ec2_transit_gateway_route_table_association.{resource_name} '
                    f'{rt_id}_{attachment_id}'
                )
                commands.append("")

        # Import Route Table Propagations
        commands.append("echo 'Importing Route Table Propagations...'")
        for rt_id, rt_resource_name in rt_resources.items():
            prop_file = self.input_dir / f'tgw-rt-propagations-{rt_id}.json'
            if not prop_file.exists():
                continue

            with open(prop_file, 'r', encoding='utf-8') as f:
                prop_data = json.load(f)

            for prop in prop_data.get('TransitGatewayRouteTablePropagations', []):
                attachment_id = prop.get('TransitGatewayAttachmentId')

                if attachment_id not in attachment_resources:
                    continue

                attachment_resource_name = attachment_resources[attachment_id]
                resource_name = f"{rt_resource_name}_prop_{attachment_resource_name}"

                commands.append(f"# Propagation: {rt_id} <-> {attachment_id}")
                commands.append(
                    f'terraform import aws_ec2_transit_gateway_route_table_propagation.{resource_name} '
                    f'{rt_id}_{attachment_id}'
                )
                commands.append("")

        # Import Transit Gateway Routes
        commands.append("echo 'Importing Transit Gateway Routes...'")
        for rt_id, rt_resource_name in rt_resources.items():
            routes_file = self.input_dir / f'tgw-rt-routes-{rt_id}.json'
            if not routes_file.exists():
                continue

            with open(routes_file, encoding='utf-8') as f:
                routes_data = json.load(f)

            for route in routes_data.get('Routes', []):
                dest_cidr = route.get('DestinationCidrBlock', '')
                if not dest_cidr or route.get('Type') == 'propagated':
                    continue

                dest_sanitized = dest_cidr.replace('/', '_').replace('.', '_')
                resource_name = f"{rt_resource_name}_route_{dest_sanitized}"

                commands.append(f"# TGW Route: {dest_cidr} in {rt_id}")
                commands.append(
                    f'terraform import aws_ec2_transit_gateway_route.{resource_name} '
                    f'{rt_id}_{dest_cidr}'
                )
                commands.append("")

        # Import VPC Routes
        commands.append("echo 'Importing VPC Routes...'")
        for rt in route_tables_data.get('RouteTables', []):
            rt_id = rt['RouteTableId']
            name = self.get_tag_value(rt.get('Tags', []), 'Name', rt_id)
            resource_name_base = self.sanitize_resource_name(name)

            routes = rt.get('Routes', [])
            for route in routes:
                if 'TransitGatewayId' not in route:
                    continue

                destination = route.get('DestinationCidrBlock', route.get('DestinationIpv6CidrBlock', ''))
                if not destination or destination == 'local':
                    continue

                dest_sanitized = destination.replace('/', '_').replace('.', '_').replace(':', '_')
                resource_name = f"{resource_name_base}_to_{dest_sanitized}"

                commands.append(f"# Route: {destination} via TGW in {name}")
                commands.append(
                    f'terraform import aws_route.{resource_name} {rt_id}_{destination}'
                )
                commands.append("")

        commands.append("echo 'Import completed!'")
        commands.append("echo 'Run terraform plan to verify the imported state matches the configuration'")
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
        '--terraform-dir',
        default=DEFAULT_TERRAFORM_DIR,
        help=f'Directory containing Terraform files (default: {DEFAULT_TERRAFORM_DIR})'
    )
    parser.add_argument(
        '--output',
        default=DEFAULT_OUTPUT_FILE,
        help=f'Output file for import commands (default: {DEFAULT_OUTPUT_FILE})'
    )

    args = parser.parse_args()

    generator = ImportCommandGenerator(args.input_dir, args.terraform_dir)
    generator.generate_to_file(args.output)


if __name__ == '__main__':
    main()
