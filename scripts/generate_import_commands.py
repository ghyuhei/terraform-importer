#!/usr/bin/env python3
"""Import Commands Generator for route-table-based directory structure.

Generates import.sh scripts for:
- terraform/tgw/import.sh : Import Transit Gateway
- terraform/rt-{name}/import.sh : Import route table and its resources

Supports multi-account and multi-region environments.

Requirements: Python 3.8+
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any

# Constants
DEFAULT_INPUT_DIR = './output'
DEFAULT_OUTPUT_DIR = './terraform'


class ImportCommandsGeneratorV2:
    """Generator for split import commands."""

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

    def generate_tgw_import(self, tgw: dict) -> str:
        """Generate import.sh for a specific Transit Gateway.

        Args:
            tgw: Transit Gateway object from AWS API

        Returns:
            String content of import.sh
        """
        tgw_id = tgw['TransitGatewayId']
        self.selected_tgw_id = tgw_id  # Store selected TGW ID

        lines = ["#!/bin/bash", "set -euo pipefail", ""]
        lines.append("echo 'Importing Transit Gateway...'")
        lines.append(f"terraform import aws_ec2_transit_gateway.this {tgw_id}")
        lines.append("")

        # Import VPC Attachments
        all_attachments = self.collect_all_attachments()
        vpc_attachments = {k: v for k, v in all_attachments.items() if v['type'] == 'vpc'}
        peering_attachments = {k: v for k, v in all_attachments.items() if v['type'] == 'peering'}

        if vpc_attachments:
            lines.append("echo 'Importing VPC Attachments...'")
            for att_id, att in vpc_attachments.items():
                att_key = att['key']
                lines.append(f"terraform import 'aws_ec2_transit_gateway_vpc_attachment.this[\"{att_key}\"]' {att_id}")
            lines.append("")

        if peering_attachments:
            lines.append("echo 'Importing Peering Attachments...'")
            for att_id, att in peering_attachments.items():
                att_key = att['key']
                lines.append(f"terraform import 'aws_ec2_transit_gateway_peering_attachment.this[\"{att_key}\"]' {att_id}")
            lines.append("")

        lines.append("echo '✓ Import completed'")
        lines.append("")

        return '\n'.join(lines)

    def collect_all_attachments(self) -> Dict[str, Any]:
        """Collect all attachment information indexed by attachment_id.

        Only collects attachments belonging to the selected TGW.
        """
        attachments = {}

        tgw_attachments_data = self.load_json('tgw-attachments.json')

        for attachment in tgw_attachments_data.get('TransitGatewayAttachments', []):
            # Filter by selected TGW ID
            if self.selected_tgw_id and attachment.get('TransitGatewayId') != self.selected_tgw_id:
                continue

            attachment_id = attachment['TransitGatewayAttachmentId']
            resource_type = attachment.get('ResourceType', '')
            name = self.get_tag_value(attachment.get('Tags'), 'Name', attachment_id)
            key = self.sanitize_key(name)

            attachments[attachment_id] = {
                'key': key,
                'type': resource_type,
                'name': name,
                'attachment_id': attachment_id,
                'resource_id': attachment.get('ResourceId', '')
            }

        return attachments

    def generate_route_table_import(self, rt_id: str, rt_name: str,
                                     rt_attachments: Dict[str, Any],
                                     associations: List[str],
                                     propagations: List[str],
                                     routes: List[Dict[str, Any]]) -> str:
        """Generate import.sh for a route table."""
        lines = ["#!/bin/bash", "set -euo pipefail", ""]
        lines.append(f"echo 'Importing resources for route table: {rt_name}'")
        lines.append("")

        # Import route table
        lines.append("# Import Route Table")
        lines.append(f"terraform import aws_ec2_transit_gateway_route_table.this {rt_id}")
        lines.append("")

        # Group attachments by type
        vpc_atts = {k: v for k, v in rt_attachments.items() if v['type'] == 'vpc'}
        peer_atts = {k: v for k, v in rt_attachments.items() if v['type'] == 'peering'}
        vpn_atts = {k: v for k, v in rt_attachments.items() if v['type'] == 'vpn'}
        dx_atts = {k: v for k, v in rt_attachments.items() if v['type'] == 'direct-connect-gateway'}

        # Note: VPC Attachments are managed in the tgw/ directory
        # Route tables only manage associations to those attachments

        # Import Associations
        if associations:
            lines.append("# Import Route Table Associations")
            for assoc_key in associations:
                # Association ID format: tgw-rtb-xxxxx_tgw-attach-xxxxx
                if assoc_key in rt_attachments:
                    att_id = rt_attachments[assoc_key]['attachment_id']
                    lines.append(f"terraform import 'aws_ec2_transit_gateway_route_table_association.this[\"{assoc_key}\"]' {rt_id}_{att_id}")
                else:
                    lines.append(f"# terraform import 'aws_ec2_transit_gateway_route_table_association.this[\"{assoc_key}\"]' {rt_id}_<attachment-id>")
            lines.append("")

        # Import Propagations
        if propagations:
            lines.append("# Import Route Table Propagations")
            for prop_key in propagations:
                # Propagation ID format: tgw-rtb-xxxxx_tgw-attach-xxxxx
                if prop_key in rt_attachments:
                    att_id = rt_attachments[prop_key]['attachment_id']
                    lines.append(f"terraform import 'aws_ec2_transit_gateway_route_table_propagation.this[\"{prop_key}\"]' {rt_id}_{att_id}")
                else:
                    lines.append(f"# terraform import 'aws_ec2_transit_gateway_route_table_propagation.this[\"{prop_key}\"]' {rt_id}_<attachment-id>")
            lines.append("")

        # Import Transit Gateway Routes
        if routes:
            lines.append("# Import Transit Gateway Routes")
            for route in routes:
                route_key = route['key']
                destination = route['destination_cidr_block']
                # Route import format: tgw-rtb-xxxxx_destination
                lines.append(f"terraform import 'aws_ec2_transit_gateway_route.this[\"{route_key}\"]' {rt_id}_{destination}")
            lines.append("")

        lines.append("echo '✓ Import completed'")
        lines.append("")

        return '\n'.join(lines)

    def generate_all_imports(self) -> None:
        """Generate all import scripts for all Transit Gateways."""
        # Load all Transit Gateways
        tgws_data = self.load_json('transit-gateways.json')
        tgws = tgws_data.get('TransitGateways', [])

        if not tgws:
            raise ValueError("No Transit Gateway found")

        print(f"Found {len(tgws)} Transit Gateway(s)")

        # Process each TGW
        for tgw in tgws:
            tgw_id = tgw['TransitGatewayId']
            tgw_name = self.get_tag_value(tgw.get('Tags'), 'Name', tgw_id)
            tgw_dirname = self.sanitize_dirname(tgw_name) if tgw_name != tgw_id else tgw_id

            # Create TGW directory
            tgw_dir = self.output_dir / f'tgw-{tgw_dirname}'
            tgw_dir.mkdir(parents=True, exist_ok=True)

            print(f"\nProcessing TGW: {tgw_name} ({tgw_id})")

            # Generate import.sh for this TGW
            tgw_import = self.generate_tgw_import(tgw)
            tgw_import_file = tgw_dir / 'import.sh'
            tgw_import_file.write_text(tgw_import, encoding='utf-8')
            tgw_import_file.chmod(0o755)
            print(f"✓ Generated: {tgw_import_file}")

            # Load route tables
            tgw_rts_data = self.load_json('tgw-route-tables.json')

            # Collect all attachments for this TGW
            all_attachments = self.collect_all_attachments()

            # Process each route table belonging to this TGW
            for rt in tgw_rts_data.get('TransitGatewayRouteTables', []):
                rt_id = rt['TransitGatewayRouteTableId']
                rt_tgw_id = rt.get('TransitGatewayId')

                # Skip route tables not belonging to this TGW
                if rt_tgw_id != tgw_id:
                    continue

                rt_name = self.get_tag_value(rt.get('Tags'), 'Name', rt_id)

                # Create route table directory
                rt_dirname = self.sanitize_dirname(rt_name)
                rt_dir = self.output_dir / f'{tgw_dirname}-rt-{rt_dirname}'
                rt_dir.mkdir(parents=True, exist_ok=True)

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
                                associations.append(att['key'])

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
                                propagations.append(att['key'])

                # Collect attachments for this route table
                rt_attachments = {}

                # Add attachments from associations
                for assoc_key in associations:
                    for att_id, att in all_attachments.items():
                        if att['key'] == assoc_key:
                            rt_attachments[assoc_key] = att
                            break

                # Add attachments from propagations
                for prop_key in propagations:
                    for att_id, att in all_attachments.items():
                        if att['key'] == prop_key and prop_key not in rt_attachments:
                            rt_attachments[prop_key] = att
                            break

                # Collect routes
                routes = []
                route_file = self.input_dir / f'tgw-rt-routes-{rt_id}.json'
                if route_file.exists():
                    with open(route_file, 'r', encoding='utf-8') as f:
                        route_data = json.load(f)
                        for route in route_data.get('Routes', []):
                            if route.get('Type') != 'static':
                                continue
                            destination = route.get('DestinationCidrBlock', '')
                            if not destination:
                                continue

                            dest_sanitized = destination.replace('/', '_').replace('.', '_').replace(':', '_')
                            route_key = f'route_{dest_sanitized}'

                            routes.append({
                                'key': route_key,
                                'destination_cidr_block': destination
                            })

                # Generate import.sh
                import_script = self.generate_route_table_import(
                    rt_id, rt_name, rt_attachments, associations, propagations, routes
                )
                import_file = rt_dir / 'import.sh'
                import_file.write_text(import_script, encoding='utf-8')
                import_file.chmod(0o755)
                print(f"✓ Generated: {import_file}")

        print(f"\n✓ All import scripts generated in: {self.output_dir}")
        print("\nNext steps:")
        print("1. For each TGW:")
        print("   cd terraform/tgw-<name>")
        print("   terraform init")
        print("   ./import.sh")
        print("   terraform apply")
        print("2. For each route table:")
        print("   cd terraform/<tgw-name>-rt-<name>")
        print("   terraform init")
        print("   Review and edit import.sh (especially for associations/propagations)")
        print("   ./import.sh")
        print("   terraform plan")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate import commands for split Terraform configuration'
    )
    parser.add_argument(
        '--input-dir',
        default=DEFAULT_INPUT_DIR,
        help=f'Directory containing AWS resource JSON files (default: {DEFAULT_INPUT_DIR})'
    )
    parser.add_argument(
        '--output-dir',
        default=DEFAULT_OUTPUT_DIR,
        help=f'Output directory for import scripts (default: {DEFAULT_OUTPUT_DIR})'
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

    generator = ImportCommandsGeneratorV2(args.input_dir, args.output_dir, account_id, region)
    generator.generate_all_imports()


if __name__ == '__main__':
    main()
