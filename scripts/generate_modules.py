#!/usr/bin/env python3
"""
Terraform Module Generator

Converts flat Terraform configuration into modular structure following best practices.
"""

import json
import os
import re
from pathlib import Path
from typing import Any

# Constants
DEFAULT_INPUT_DIR = './terraform'
DEFAULT_OUTPUT_DIR = './terraform-modules'
MODULE_NAME = 'transit-gateway'


class TerraformModuleGenerator:
    """Generate Terraform modules from flat configuration."""

    def __init__(self, input_dir: str, output_dir: str):
        """
        Initialize the generator.

        Args:
            input_dir: Directory containing flat Terraform files
            output_dir: Directory to output modular structure
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.module_dir = self.output_dir / 'modules' / MODULE_NAME

    def generate(self) -> None:
        """Generate modular Terraform structure."""
        print(f"Generating Terraform modules from: {self.input_dir}")

        # Create directory structure
        self._create_directories()

        # Read existing Terraform files
        resources = self._read_terraform_files()

        # Generate module files
        self._generate_module_main(resources)
        self._generate_module_variables(resources)
        self._generate_module_outputs(resources)
        self._generate_module_readme(resources)

        # Generate root module files
        self._generate_root_main(resources)
        self._generate_root_variables(resources)
        self._generate_root_outputs()
        self._generate_root_versions()

        print(f"\n✓ Module structure generated in: {self.output_dir}")
        print(f"  - Module: {self.module_dir}")
        print(f"  - Root: {self.output_dir}")

    def _create_directories(self) -> None:
        """Create module directory structure."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.module_dir.mkdir(parents=True, exist_ok=True)

    def _read_terraform_files(self) -> dict[str, str]:
        """Read all .tf files from input directory."""
        resources = {}

        for tf_file in self.input_dir.glob('*.tf'):
            if tf_file.name == 'provider.tf':
                continue

            with open(tf_file, 'r', encoding='utf-8') as f:
                resources[tf_file.stem] = f.read()

        return resources

    def _generate_module_main(self, resources: dict[str, str]) -> None:
        """Generate module main.tf with all resources."""
        main_content = []

        # Add header
        main_content.append('# Transit Gateway Module\n')
        main_content.append('# This module manages AWS Transit Gateway and related resources\n\n')

        # Process each resource file
        for name, content in sorted(resources.items()):
            # Skip if empty
            if not content.strip():
                continue

            # Replace hardcoded values with variables
            processed_content = self._replace_with_variables(content)
            main_content.append(processed_content)
            main_content.append('\n')

        output_file = self.module_dir / 'main.tf'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(''.join(main_content))

        print(f"✓ Generated {output_file.relative_to(self.output_dir)}")

    def _replace_with_variables(self, content: str) -> str:
        """Replace hardcoded values with variable references."""
        # This is a simplified version - in production you'd want more sophisticated parsing
        return content

    def _generate_module_variables(self, resources: dict[str, str]) -> None:
        """Generate module variables.tf."""
        variables_content = '''# Module Variables

variable "tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "transit_gateway_amazon_side_asn" {
  description = "Amazon side ASN for Transit Gateway"
  type        = number
  default     = 64512
}

variable "transit_gateway_description" {
  description = "Description for Transit Gateway"
  type        = string
  default     = "Managed by Terraform"
}

variable "transit_gateway_auto_accept_shared_attachments" {
  description = "Whether resource attachment requests are automatically accepted"
  type        = string
  default     = "disable"
}

variable "transit_gateway_default_route_table_association" {
  description = "Whether resource attachments are automatically associated with the default route table"
  type        = string
  default     = "disable"
}

variable "transit_gateway_default_route_table_propagation" {
  description = "Whether resource attachments automatically propagate routes to the default route table"
  type        = string
  default     = "disable"
}

variable "transit_gateway_dns_support" {
  description = "Whether DNS support is enabled"
  type        = string
  default     = "enable"
}

variable "transit_gateway_vpn_ecmp_support" {
  description = "Whether VPN ECMP support is enabled"
  type        = string
  default     = "enable"
}
'''

        output_file = self.module_dir / 'variables.tf'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(variables_content)

        print(f"✓ Generated {output_file.relative_to(self.output_dir)}")

    def _generate_module_outputs(self, resources: dict[str, str]) -> None:
        """Generate module outputs.tf."""
        outputs_content = '''# Module Outputs

output "transit_gateway_id" {
  description = "Transit Gateway ID"
  value       = try(aws_ec2_transit_gateway.multi_vpc_tgw.id, null)
}

output "transit_gateway_arn" {
  description = "Transit Gateway ARN"
  value       = try(aws_ec2_transit_gateway.multi_vpc_tgw.arn, null)
}

output "transit_gateway_owner_id" {
  description = "Transit Gateway Owner ID"
  value       = try(aws_ec2_transit_gateway.multi_vpc_tgw.owner_id, null)
}

output "route_table_ids" {
  description = "Map of route table names to IDs"
  value = {
    production  = try(aws_ec2_transit_gateway_route_table.tgw_rt_production.id, null)
    development = try(aws_ec2_transit_gateway_route_table.tgw_rt_development.id, null)
    shared      = try(aws_ec2_transit_gateway_route_table.tgw_rt_shared.id, null)
  }
}

output "vpc_attachment_ids" {
  description = "Map of VPC attachment names to IDs"
  value = {
    vpc1 = try(aws_ec2_transit_gateway_vpc_attachment.tgw_attachment_vpc1.id, null)
    vpc2 = try(aws_ec2_transit_gateway_vpc_attachment.tgw_attachment_vpc2.id, null)
  }
}
'''

        output_file = self.module_dir / 'outputs.tf'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(outputs_content)

        print(f"✓ Generated {output_file.relative_to(self.output_dir)}")

    def _generate_module_readme(self, resources: dict[str, str]) -> None:
        """Generate module README.md."""
        readme_content = '''# Transit Gateway Module

このモジュールはAWS Transit Gatewayおよび関連リソースを管理します。

## 使用方法

```hcl
module "transit_gateway" {
  source = "./modules/transit-gateway"

  transit_gateway_description = "Production Transit Gateway"
  transit_gateway_amazon_side_asn = 64512

  tags = {
    Environment = "production"
    ManagedBy   = "terraform"
  }
}
```

## Requirements

| Name | Version |
|------|---------|
| terraform | >= 1.5 |
| aws | ~> 5.0 |

## Resources

| Type | Count |
|------|-------|
| aws_ec2_transit_gateway | 1 |
| aws_ec2_transit_gateway_route_table | 3 |
| aws_ec2_transit_gateway_vpc_attachment | 2 |
| aws_ec2_transit_gateway_route | 12 |
| aws_route | 4 |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| tags | Common tags to apply to all resources | `map(string)` | `{}` | no |
| transit_gateway_description | Description for Transit Gateway | `string` | `"Managed by Terraform"` | no |
| transit_gateway_amazon_side_asn | Amazon side ASN | `number` | `64512` | no |

## Outputs

| Name | Description |
|------|-------------|
| transit_gateway_id | Transit Gateway ID |
| transit_gateway_arn | Transit Gateway ARN |
| route_table_ids | Map of route table IDs |
| vpc_attachment_ids | Map of VPC attachment IDs |
'''

        output_file = self.module_dir / 'README.md'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)

        print(f"✓ Generated {output_file.relative_to(self.output_dir)}")

    def _generate_root_main(self, resources: dict[str, str]) -> None:
        """Generate root main.tf that calls the module."""
        main_content = '''# Root Module - Transit Gateway Infrastructure

module "transit_gateway" {
  source = "./modules/transit-gateway"

  transit_gateway_description                    = "Multi-VPC Transit Gateway"
  transit_gateway_amazon_side_asn                = 64512
  transit_gateway_auto_accept_shared_attachments = "enable"
  transit_gateway_default_route_table_association = "disable"
  transit_gateway_default_route_table_propagation = "disable"
  transit_gateway_dns_support                    = "enable"
  transit_gateway_vpn_ecmp_support              = "enable"

  tags = {
    ManagedBy = "Terraform"
    Project   = "TransitGateway"
  }
}
'''

        output_file = self.output_dir / 'main.tf'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(main_content)

        print(f"✓ Generated {output_file.relative_to(self.output_dir)}")

    def _generate_root_variables(self, resources: dict[str, str]) -> None:
        """Generate root variables.tf."""
        variables_content = '''# Root Module Variables

variable "region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-1"
}

variable "environment" {
  description = "Environment name (e.g., production, staging, development)"
  type        = string
  default     = "production"
}
'''

        output_file = self.output_dir / 'variables.tf'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(variables_content)

        print(f"✓ Generated {output_file.relative_to(self.output_dir)}")

    def _generate_root_outputs(self) -> None:
        """Generate root outputs.tf."""
        outputs_content = '''# Root Module Outputs

output "transit_gateway_id" {
  description = "Transit Gateway ID"
  value       = module.transit_gateway.transit_gateway_id
}

output "transit_gateway_arn" {
  description = "Transit Gateway ARN"
  value       = module.transit_gateway.transit_gateway_arn
}

output "route_table_ids" {
  description = "Transit Gateway Route Table IDs"
  value       = module.transit_gateway.route_table_ids
}

output "vpc_attachment_ids" {
  description = "VPC Attachment IDs"
  value       = module.transit_gateway.vpc_attachment_ids
}
'''

        output_file = self.output_dir / 'outputs.tf'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(outputs_content)

        print(f"✓ Generated {output_file.relative_to(self.output_dir)}")

    def _generate_root_versions(self) -> None:
        """Generate root versions.tf."""
        versions_content = '''terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      ManagedBy   = "Terraform"
      Environment = var.environment
    }
  }
}
'''

        output_file = self.output_dir / 'versions.tf'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(versions_content)

        print(f"✓ Generated {output_file.relative_to(self.output_dir)}")


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate Terraform modules from flat configuration'
    )
    parser.add_argument(
        '--input-dir',
        default=DEFAULT_INPUT_DIR,
        help=f'Input directory with flat Terraform files (default: {DEFAULT_INPUT_DIR})'
    )
    parser.add_argument(
        '--output-dir',
        default=DEFAULT_OUTPUT_DIR,
        help=f'Output directory for modular structure (default: {DEFAULT_OUTPUT_DIR})'
    )

    args = parser.parse_args()

    generator = TerraformModuleGenerator(args.input_dir, args.output_dir)
    generator.generate()


if __name__ == '__main__':
    main()
