#!/usr/bin/env python3
"""Transit Gateway Terraform Generator.

Reads AWS resource data and generates Terraform configuration files
for Transit Gateways, Route Tables, Attachments, and related resources.

Requirements: Python 3.8+
"""

import json
from pathlib import Path

# Constants
DEFAULT_INPUT_DIR = './output'
DEFAULT_OUTPUT_DIR = './terraform'
DEFAULT_REGION = 'ap-northeast-1'
REQUIRED_TF_VERSION = '>= 1.5'
AWS_PROVIDER_VERSION = '~> 5.0'


class TerraformGenerator:
    """Generator for Terraform configuration from AWS Transit Gateway resources."""

    def __init__(self, input_dir: str, output_dir: str, region: str) -> None:
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.region = region
        self.output_dir.mkdir(parents=True, exist_ok=True)

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

    def format_tag_key(self, key: str) -> str:
        """Format tag key for Terraform. Quote if contains special characters."""
        if ':' in key or '-' in key or ' ' in key:
            return f'"{key}"'
        return key

    def generate_transit_gateway(self, tgw: dict) -> tuple[str, str, str]:
        """Generate Terraform code for Transit Gateway."""
        tgw_id = tgw['TransitGatewayId']
        name = self.get_tag_value(tgw.get('Tags', []), 'Name', tgw_id)
        resource_name = self.sanitize_resource_name(name)

        options = tgw.get('Options', {})
        description = tgw.get('Description', '')

        # Build description line if present
        description_line = f'  description                     = "{description}"\n' if description else ''

        tf_code = f'''# Transit Gateway: {name}
resource "aws_ec2_transit_gateway" "{resource_name}" {{
{description_line}  amazon_side_asn                 = {options.get('AmazonSideAsn', 64512)}
  default_route_table_association = "{options.get('DefaultRouteTableAssociation', 'enable')}"
  default_route_table_propagation = "{options.get('DefaultRouteTablePropagation', 'enable')}"
  dns_support                     = "{options.get('DnsSupport', 'enable')}"
  vpn_ecmp_support               = "{options.get('VpnEcmpSupport', 'enable')}"
  auto_accept_shared_attachments = "{options.get('AutoAcceptSharedAttachments', 'disable')}"

  tags = {{
    Name = "{name}"
'''

        for tag in tgw.get('Tags', []):
            if tag['Key'] != 'Name':
                tag_key = self.format_tag_key(tag['Key'])
                tf_code += f'    {tag_key} = "{tag["Value"]}"\n'

        tf_code += '  }\n}\n\n'
        return tf_code, resource_name, tgw_id

    def generate_tgw_route_table(self, rt: dict, tgw_resource_name: str) -> tuple[str, str, str]:
        """Generate Terraform code for Transit Gateway Route Table."""
        rt_id = rt['TransitGatewayRouteTableId']
        name = self.get_tag_value(rt.get('Tags', []), 'Name', rt_id)
        resource_name = self.sanitize_resource_name(name)

        tf_code = f'''# Transit Gateway Route Table: {name}
resource "aws_ec2_transit_gateway_route_table" "{resource_name}" {{
  transit_gateway_id = aws_ec2_transit_gateway.{tgw_resource_name}.id

  tags = {{
    Name = "{name}"
'''

        for tag in rt.get('Tags', []):
            if tag['Key'] != 'Name':
                tag_key = self.format_tag_key(tag['Key'])
                tf_code += f'    {tag_key} = "{tag["Value"]}"\n'

        tf_code += '  }\n}\n\n'
        return tf_code, resource_name, rt_id

    def generate_tgw_vpc_attachment(self, attachment: dict, tgw_resource_name: str) -> tuple[str, str, str]:
        """Generate Terraform code for Transit Gateway VPC Attachment."""
        attachment_id = attachment['TransitGatewayAttachmentId']
        name = self.get_tag_value(attachment.get('Tags', []), 'Name', attachment_id)
        resource_name = self.sanitize_resource_name(name)

        # Handle VPC attachments only
        if attachment.get('ResourceType') != 'vpc':
            return "", resource_name, attachment_id

        options = attachment.get('Options') or {}
        subnet_ids = attachment.get('SubnetIds') or []

        # Determine what to ignore in lifecycle
        ignore_list = []
        if not subnet_ids:
            subnet_ids = ["PLACEHOLDER"]
            ignore_list.append("subnet_ids")

        # If options is None/empty, ignore option fields
        if not attachment.get('Options'):
            ignore_list.extend(["appliance_mode_support", "dns_support", "ipv6_support"])

        # Build lifecycle block if needed
        lifecycle_block = ""
        if ignore_list:
            ignore_items = ", ".join(ignore_list)
            lifecycle_block = f'''
  lifecycle {{
    ignore_changes = [{ignore_items}]
  }}
'''

        tf_code = f'''# Transit Gateway VPC Attachment: {name}
resource "aws_ec2_transit_gateway_vpc_attachment" "{resource_name}" {{
  transit_gateway_id = aws_ec2_transit_gateway.{tgw_resource_name}.id
  vpc_id             = "{attachment.get('ResourceId', '')}"
  subnet_ids         = {json.dumps(subnet_ids)}

  appliance_mode_support = "{options.get('ApplianceModeSupport', 'disable')}"
  dns_support            = "{options.get('DnsSupport', 'enable')}"
  ipv6_support           = "{options.get('Ipv6Support', 'disable')}"
{lifecycle_block}
  tags = {{
    Name = "{name}"
'''

        for tag in attachment.get('Tags', []):
            if tag['Key'] != 'Name':
                tag_key = self.format_tag_key(tag['Key'])
                tf_code += f'    {tag_key} = "{tag["Value"]}"\n'

        tf_code += '  }\n}\n\n'
        return tf_code, resource_name, attachment_id

    def generate_tgw_route_table_association(
        self, assoc: dict, rt_resource_name: str, attachment_resources: dict
    ) -> str:
        """Generate Terraform code for Transit Gateway Route Table Association."""
        attachment_id = assoc.get('TransitGatewayAttachmentId')

        if attachment_id not in attachment_resources:
            return ""

        attachment_resource_name = attachment_resources[attachment_id]
        resource_name = f"{rt_resource_name}_assoc_{attachment_resource_name}"

        tf_code = f'''# Transit Gateway Route Table Association
resource "aws_ec2_transit_gateway_route_table_association" "{resource_name}" {{
  transit_gateway_attachment_id  = aws_ec2_transit_gateway_vpc_attachment.{attachment_resource_name}.id
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.{rt_resource_name}.id
}}

'''
        return tf_code

    def generate_tgw_route_table_propagation(
        self, prop: dict, rt_resource_name: str, attachment_resources: dict
    ) -> str:
        """Generate Terraform code for Transit Gateway Route Table Propagation."""
        attachment_id = prop.get('TransitGatewayAttachmentId')

        if attachment_id not in attachment_resources:
            return ""

        attachment_resource_name = attachment_resources[attachment_id]
        resource_name = f"{rt_resource_name}_prop_{attachment_resource_name}"

        tf_code = f'''# Transit Gateway Route Table Propagation
resource "aws_ec2_transit_gateway_route_table_propagation" "{resource_name}" {{
  transit_gateway_attachment_id  = aws_ec2_transit_gateway_vpc_attachment.{attachment_resource_name}.id
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.{rt_resource_name}.id
}}

'''
        return tf_code

    def generate_tgw_route(self, route: dict, rt_resource_name: str, rt_id: str, attachment_resources: dict) -> str:
        """Generate Terraform code for Transit Gateway Route."""
        dest_cidr = route.get('DestinationCidrBlock', '')
        if not dest_cidr:
            return ""

        # Skip propagated routes (Type=propagated)
        if route.get('Type') == 'propagated':
            return ""

        attachment_id = route.get('TransitGatewayAttachments', [{}])[0].get('TransitGatewayAttachmentId')
        is_blackhole = route.get('State') == 'blackhole'

        # Sanitize CIDR for resource name
        dest_sanitized = dest_cidr.replace('/', '_').replace('.', '_')
        resource_name = f"{rt_resource_name}_route_{dest_sanitized}"

        tf_code = f'''# TGW Route: {dest_cidr} in {rt_resource_name}
resource "aws_ec2_transit_gateway_route" "{resource_name}" {{
  destination_cidr_block         = "{dest_cidr}"
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.{rt_resource_name}.id
'''

        if is_blackhole:
            tf_code += '  blackhole              = true\n'
        elif attachment_id and attachment_id in attachment_resources:
            attachment_resource = attachment_resources[attachment_id]
            tf_code += f'  transit_gateway_attachment_id  = aws_ec2_transit_gateway_vpc_attachment.{attachment_resource}.id\n'

        tf_code += '}\n\n'
        return tf_code

    def generate_vpc_route(self, route_table: dict) -> str:
        """Generate Terraform code for VPC Route Table routes pointing to TGW."""
        rt_id = route_table['RouteTableId']
        name = self.get_tag_value(route_table.get('Tags', []), 'Name', rt_id)
        resource_name_base = self.sanitize_resource_name(name)

        tf_code = ""
        routes = route_table.get('Routes', [])

        for route in routes:
            # Only handle routes with Transit Gateway as destination
            if 'TransitGatewayId' not in route:
                continue

            destination = route.get('DestinationCidrBlock', route.get('DestinationIpv6CidrBlock', ''))
            if not destination or destination == 'local':
                continue

            # Sanitize destination for resource name
            dest_sanitized = destination.replace('/', '_').replace('.', '_').replace(':', '_')
            resource_name = f"{resource_name_base}_to_{dest_sanitized}"

            tf_code += f'''# Route: {destination} via TGW in {name}
resource "aws_route" "{resource_name}" {{
  route_table_id         = "{rt_id}"
  destination_cidr_block = "{destination}"
  transit_gateway_id     = "{route['TransitGatewayId']}"
}}

'''

        return tf_code

    def write_file(self, filename: str, content: str) -> None:
        """Write content to a file in the output directory."""
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Generated {filename}")

    def generate_all(self) -> None:
        """Generate all Terraform configuration files."""
        print(f"Generating Terraform configuration for region: {self.region}")
        print()

        # Load all data
        tgws_data = self.load_json('transit-gateways.json')
        tgw_rts_data = self.load_json('tgw-route-tables.json')
        tgw_attachments_data = self.load_json('tgw-attachments.json')
        route_tables_data = self.load_json('route-tables.json')

        # Maps to track resource relationships
        tgw_resources = {}  # tgw_id -> resource_name
        rt_resources = {}   # rt_id -> resource_name
        attachment_resources = {}  # attachment_id -> resource_name

        # Generate Transit Gateways
        tgw_code = "# Transit Gateways\n\n"
        for tgw in tgws_data.get('TransitGateways', []):
            code, resource_name, tgw_id = self.generate_transit_gateway(tgw)
            tgw_code += code
            tgw_resources[tgw_id] = resource_name

        self.write_file('transit_gateways.tf', tgw_code)

        # Generate Transit Gateway Route Tables
        rt_code = "# Transit Gateway Route Tables\n\n"
        for rt in tgw_rts_data.get('TransitGatewayRouteTables', []):
            tgw_id = rt['TransitGatewayId']
            if tgw_id not in tgw_resources:
                continue
            code, resource_name, rt_id = self.generate_tgw_route_table(rt, tgw_resources[tgw_id])
            rt_code += code
            rt_resources[rt_id] = resource_name

        self.write_file('tgw_route_tables.tf', rt_code)

        # Generate Transit Gateway VPC Attachments
        attachment_code = "# Transit Gateway VPC Attachments\n\n"
        for attachment in tgw_attachments_data.get('TransitGatewayAttachments', []):
            tgw_id = attachment['TransitGatewayId']
            if tgw_id not in tgw_resources:
                continue
            code, resource_name, attachment_id = self.generate_tgw_vpc_attachment(
                attachment, tgw_resources[tgw_id]
            )
            if code:
                attachment_code += code
                attachment_resources[attachment_id] = resource_name

        self.write_file('tgw_attachments.tf', attachment_code)

        # Generate Route Table Associations and Propagations
        assoc_code = "# Transit Gateway Route Table Associations and Propagations\n\n"

        for rt_id, rt_resource_name in rt_resources.items():
            # Load associations
            assoc_file = self.input_dir / f'tgw-rt-associations-{rt_id}.json'
            if assoc_file.exists():
                with open(assoc_file, 'r', encoding='utf-8') as f:
                    assoc_data = json.load(f)
                for assoc in assoc_data.get('Associations', []):
                    code = self.generate_tgw_route_table_association(
                        assoc, rt_resource_name, attachment_resources
                    )
                    assoc_code += code

            # Load propagations
            prop_file = self.input_dir / f'tgw-rt-propagations-{rt_id}.json'
            if prop_file.exists():
                with open(prop_file, 'r', encoding='utf-8') as f:
                    prop_data = json.load(f)
                for prop in prop_data.get('TransitGatewayRouteTablePropagations', []):
                    code = self.generate_tgw_route_table_propagation(
                        prop, rt_resource_name, attachment_resources
                    )
                    assoc_code += code

        self.write_file('tgw_associations.tf', assoc_code)

        # Generate Transit Gateway Routes (static routes in TGW route tables)
        tgw_routes_code = "# Transit Gateway Routes\n\n"
        for rt_id, rt_resource_name in rt_resources.items():
            routes_file = self.input_dir / f'tgw-rt-routes-{rt_id}.json'
            if routes_file.exists():
                with open(routes_file, encoding='utf-8') as f:
                    routes_data = json.load(f)
                for route in routes_data.get('Routes', []):
                    code = self.generate_tgw_route(route, rt_resource_name, rt_id, attachment_resources)
                    if code:
                        tgw_routes_code += code

        self.write_file('tgw_routes.tf', tgw_routes_code)

        # Generate VPC Route Table routes pointing to TGW
        routes_code = "# VPC Routes to Transit Gateway\n\n"
        for rt in route_tables_data.get('RouteTables', []):
            code = self.generate_vpc_route(rt)
            if code:
                routes_code += code

        self.write_file('vpc_routes.tf', routes_code)

        # Generate provider configuration
        provider_code = f'''terraform {{
  required_version = "{REQUIRED_TF_VERSION}"

  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "{AWS_PROVIDER_VERSION}"
    }}
  }}
}}

provider "aws" {{
  region = "{self.region}"
}}
'''

        self.write_file('provider.tf', provider_code)

        print()
        print(f"✓ All Terraform files generated in: {self.output_dir}")
        print()
        print("Summary:")
        print(f"  - Transit Gateways: {len(tgw_resources)}")
        print(f"  - Route Tables: {len(rt_resources)}")
        print(f"  - VPC Attachments: {len(attachment_resources)}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate Terraform configuration from AWS Transit Gateway resources'
    )
    parser.add_argument(
        '--input-dir',
        default=DEFAULT_INPUT_DIR,
        help=f'Directory containing AWS resource JSON files (default: {DEFAULT_INPUT_DIR})'
    )
    parser.add_argument(
        '--output-dir',
        default=DEFAULT_OUTPUT_DIR,
        help=f'Directory to output Terraform files (default: {DEFAULT_OUTPUT_DIR})'
    )
    parser.add_argument(
        '--region',
        default=DEFAULT_REGION,
        help=f'AWS region (default: {DEFAULT_REGION})'
    )

    args = parser.parse_args()

    generator = TerraformGenerator(args.input_dir, args.output_dir, args.region)
    generator.generate_all()


if __name__ == '__main__':
    main()
