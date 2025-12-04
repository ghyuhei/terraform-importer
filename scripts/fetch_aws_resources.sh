#!/bin/bash
set -euo pipefail

OUTPUT_DIR="${OUTPUT_DIR:-./output}"
REGION="${AWS_REGION:-ap-northeast-1}"

mkdir -p "$OUTPUT_DIR"

echo "Fetching resources from region: $REGION"

# Transit Gateways
aws ec2 describe-transit-gateways --region "$REGION" --output json > "$OUTPUT_DIR/transit-gateways.json"

TGW_IDS=$(aws ec2 describe-transit-gateways --region "$REGION" \
  --query 'TransitGateways[*].TransitGatewayId' --output text)

[ -z "$TGW_IDS" ] && echo "No Transit Gateways found" && exit 0

# Route Tables & Attachments
aws ec2 describe-transit-gateway-route-tables --region "$REGION" --output json > "$OUTPUT_DIR/tgw-route-tables.json"
aws ec2 describe-transit-gateway-attachments --region "$REGION" --output json > "$OUTPUT_DIR/tgw-attachments.json"
aws ec2 describe-route-tables --region "$REGION" --output json > "$OUTPUT_DIR/route-tables.json"

# Get detailed VPC attachment information including subnet_ids
ATTACHMENT_IDS=$(aws ec2 describe-transit-gateway-attachments --region "$REGION" \
  --filters "Name=resource-type,Values=vpc" \
  --query 'TransitGatewayAttachments[*].TransitGatewayAttachmentId' --output text)

for ATT_ID in $ATTACHMENT_IDS; do
  aws ec2 describe-transit-gateway-vpc-attachments --region "$REGION" \
    --transit-gateway-attachment-ids "$ATT_ID" --output json > "$OUTPUT_DIR/tgw-vpc-attachment-$ATT_ID.json"
done

# Get peering attachments (for inter-region peering)
PEERING_IDS=$(aws ec2 describe-transit-gateway-attachments --region "$REGION" \
  --filters "Name=resource-type,Values=peering" \
  --query 'TransitGatewayAttachments[*].TransitGatewayAttachmentId' --output text)

for PEER_ID in $PEERING_IDS; do
  aws ec2 describe-transit-gateway-peering-attachments --region "$REGION" \
    --transit-gateway-attachment-ids "$PEER_ID" --output json > "$OUTPUT_DIR/tgw-peering-attachment-$PEER_ID.json"
done

# Associations & Propagations
for TGW_ID in $TGW_IDS; do
  RT_IDS=$(aws ec2 describe-transit-gateway-route-tables --region "$REGION" \
    --filters "Name=transit-gateway-id,Values=$TGW_ID" \
    --query 'TransitGatewayRouteTables[*].TransitGatewayRouteTableId' --output text)

  for RT_ID in $RT_IDS; do
    aws ec2 get-transit-gateway-route-table-associations --region "$REGION" \
      --transit-gateway-route-table-id "$RT_ID" --output json > "$OUTPUT_DIR/tgw-rt-associations-$RT_ID.json"
    aws ec2 get-transit-gateway-route-table-propagations --region "$REGION" \
      --transit-gateway-route-table-id "$RT_ID" --output json > "$OUTPUT_DIR/tgw-rt-propagations-$RT_ID.json"
    aws ec2 search-transit-gateway-routes --region "$REGION" \
      --transit-gateway-route-table-id "$RT_ID" \
      --filters "Name=state,Values=active,blackhole" --output json > "$OUTPUT_DIR/tgw-rt-routes-$RT_ID.json"
  done
done

TGW_COUNT=$(jq '.TransitGateways | length' "$OUTPUT_DIR/transit-gateways.json")
RT_COUNT=$(jq '.TransitGatewayRouteTables | length' "$OUTPUT_DIR/tgw-route-tables.json")
ATT_COUNT=$(jq '.TransitGatewayAttachments | length' "$OUTPUT_DIR/tgw-attachments.json")

echo "✓ Completed: $OUTPUT_DIR"
echo "  TGW: $TGW_COUNT, Route Tables: $RT_COUNT, Attachments: $ATT_COUNT"
