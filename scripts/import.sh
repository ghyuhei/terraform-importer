#!/bin/bash

# Terraform Import Commands
# Auto-generated script to import existing AWS resources into Terraform

set -euo pipefail

cd "/home/yhino/work/git/terraform-importer/terraform"

echo 'Importing Transit Gateways...'
# Transit Gateway: multi-vpc-tgw
terraform import aws_ec2_transit_gateway.multi_vpc_tgw tgw-0aa7ee39a5c5108ea

echo 'Importing Transit Gateway Route Tables...'
# Route Table: tgw-rt-development
terraform import aws_ec2_transit_gateway_route_table.tgw_rt_development tgw-rtb-037a079c79198f9ea

# Route Table: tgw-rt-production
terraform import aws_ec2_transit_gateway_route_table.tgw_rt_production tgw-rtb-09d21753745036ef7

# Route Table: tgw-rt-shared
terraform import aws_ec2_transit_gateway_route_table.tgw_rt_shared tgw-rtb-0b99db09b9becaf34

echo 'Importing Transit Gateway VPC Attachments...'
# VPC Attachment: tgw-attachment-vpc2
terraform import aws_ec2_transit_gateway_vpc_attachment.tgw_attachment_vpc2 tgw-attach-05ba931d7d6d9c8ce

# VPC Attachment: tgw-attachment-vpc1
terraform import aws_ec2_transit_gateway_vpc_attachment.tgw_attachment_vpc1 tgw-attach-0b4cd91f33d694581

echo 'Importing Route Table Associations...'
# Association: tgw-rtb-037a079c79198f9ea <-> tgw-attach-05ba931d7d6d9c8ce
terraform import aws_ec2_transit_gateway_route_table_association.tgw_rt_development_assoc_tgw_attachment_vpc2 tgw-rtb-037a079c79198f9ea_tgw-attach-05ba931d7d6d9c8ce

# Association: tgw-rtb-09d21753745036ef7 <-> tgw-attach-0b4cd91f33d694581
terraform import aws_ec2_transit_gateway_route_table_association.tgw_rt_production_assoc_tgw_attachment_vpc1 tgw-rtb-09d21753745036ef7_tgw-attach-0b4cd91f33d694581

echo 'Importing Route Table Propagations...'
# Propagation: tgw-rtb-0b99db09b9becaf34 <-> tgw-attach-05ba931d7d6d9c8ce
terraform import aws_ec2_transit_gateway_route_table_propagation.tgw_rt_shared_prop_tgw_attachment_vpc2 tgw-rtb-0b99db09b9becaf34_tgw-attach-05ba931d7d6d9c8ce

# Propagation: tgw-rtb-0b99db09b9becaf34 <-> tgw-attach-0b4cd91f33d694581
terraform import aws_ec2_transit_gateway_route_table_propagation.tgw_rt_shared_prop_tgw_attachment_vpc1 tgw-rtb-0b99db09b9becaf34_tgw-attach-0b4cd91f33d694581

echo 'Importing Transit Gateway Routes...'
# TGW Route: 10.1.0.0/16 in tgw-rtb-037a079c79198f9ea
terraform import aws_ec2_transit_gateway_route.tgw_rt_development_route_10_1_0_0_16 tgw-rtb-037a079c79198f9ea_10.1.0.0/16

# TGW Route: 10.1.100.0/24 in tgw-rtb-037a079c79198f9ea
terraform import aws_ec2_transit_gateway_route.tgw_rt_development_route_10_1_100_0_24 tgw-rtb-037a079c79198f9ea_10.1.100.0/24

# TGW Route: 10.1.101.0/24 in tgw-rtb-037a079c79198f9ea
terraform import aws_ec2_transit_gateway_route.tgw_rt_development_route_10_1_101_0_24 tgw-rtb-037a079c79198f9ea_10.1.101.0/24

# TGW Route: 192.168.0.0/16 in tgw-rtb-037a079c79198f9ea
terraform import aws_ec2_transit_gateway_route.tgw_rt_development_route_192_168_0_0_16 tgw-rtb-037a079c79198f9ea_192.168.0.0/16

# TGW Route: 10.2.0.0/16 in tgw-rtb-09d21753745036ef7
terraform import aws_ec2_transit_gateway_route.tgw_rt_production_route_10_2_0_0_16 tgw-rtb-09d21753745036ef7_10.2.0.0/16

# TGW Route: 10.2.128.0/24 in tgw-rtb-09d21753745036ef7
terraform import aws_ec2_transit_gateway_route.tgw_rt_production_route_10_2_128_0_24 tgw-rtb-09d21753745036ef7_10.2.128.0/24

# TGW Route: 10.2.129.0/24 in tgw-rtb-09d21753745036ef7
terraform import aws_ec2_transit_gateway_route.tgw_rt_production_route_10_2_129_0_24 tgw-rtb-09d21753745036ef7_10.2.129.0/24

# TGW Route: 10.99.0.0/16 in tgw-rtb-09d21753745036ef7
terraform import aws_ec2_transit_gateway_route.tgw_rt_production_route_10_99_0_0_16 tgw-rtb-09d21753745036ef7_10.99.0.0/16

# TGW Route: 0.0.0.0/0 in tgw-rtb-0b99db09b9becaf34
terraform import aws_ec2_transit_gateway_route.tgw_rt_shared_route_0_0_0_0_0 tgw-rtb-0b99db09b9becaf34_0.0.0.0/0

# TGW Route: 10.1.0.0/16 in tgw-rtb-0b99db09b9becaf34
terraform import aws_ec2_transit_gateway_route.tgw_rt_shared_route_10_1_0_0_16 tgw-rtb-0b99db09b9becaf34_10.1.0.0/16

# TGW Route: 10.2.0.0/16 in tgw-rtb-0b99db09b9becaf34
terraform import aws_ec2_transit_gateway_route.tgw_rt_shared_route_10_2_0_0_16 tgw-rtb-0b99db09b9becaf34_10.2.0.0/16

# TGW Route: 172.16.0.0/12 in tgw-rtb-0b99db09b9becaf34
terraform import aws_ec2_transit_gateway_route.tgw_rt_shared_route_172_16_0_0_12 tgw-rtb-0b99db09b9becaf34_172.16.0.0/12

echo 'Importing VPC Routes...'
# Route: 10.2.0.0/16 via TGW in vpc1-route-table
terraform import aws_route.vpc1_route_table_to_10_2_0_0_16 rtb-078b6f8b907f90717_10.2.0.0/16

# Route: 172.16.0.0/12 via TGW in vpc1-route-table
terraform import aws_route.vpc1_route_table_to_172_16_0_0_12 rtb-078b6f8b907f90717_172.16.0.0/12

# Route: 10.1.100.0/24 via TGW in vpc2-route-table
terraform import aws_route.vpc2_route_table_to_10_1_100_0_24 rtb-0583ca2804730d30d_10.1.100.0/24

# Route: 10.1.0.0/16 via TGW in vpc2-route-table
terraform import aws_route.vpc2_route_table_to_10_1_0_0_16 rtb-0583ca2804730d30d_10.1.0.0/16

echo 'Import completed!'
echo 'Run terraform plan to verify the imported state matches the configuration'
