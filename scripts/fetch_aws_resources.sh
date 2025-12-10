#!/bin/bash
set -euo pipefail

OUTPUT_DIR="${OUTPUT_DIR:-./output}"
REGION="${AWS_REGION:-ap-northeast-1}"
AWS_PROFILE="${AWS_PROFILE:-}"
ACCOUNT_ID="${AWS_ACCOUNT_ID:-}"

# Set up AWS profile if specified
if [ -n "$AWS_PROFILE" ]; then
  PROFILE_ARG="--profile $AWS_PROFILE"
else
  PROFILE_ARG=""
fi

# Get account ID if not specified
if [ -z "$ACCOUNT_ID" ]; then
  ACCOUNT_ID=$(aws sts get-caller-identity $PROFILE_ARG --query 'Account' --output text)
fi

# Create output directory with account and region
OUTPUT_DIR="${OUTPUT_DIR}/${ACCOUNT_ID}/${REGION}"
mkdir -p "$OUTPUT_DIR"

echo "Fetching resources:"
echo "  Account: $ACCOUNT_ID"
echo "  Region:  $REGION"
echo "  Profile: ${AWS_PROFILE:-default}"
echo "  Output:  $OUTPUT_DIR"
echo ""

# Transit Gateways
aws ec2 describe-transit-gateways $PROFILE_ARG --region "$REGION" --output json > "$OUTPUT_DIR/transit-gateways.json"

TGW_IDS=$(aws ec2 describe-transit-gateways $PROFILE_ARG --region "$REGION" \
  --query 'TransitGateways[*].TransitGatewayId' --output text)

[ -z "$TGW_IDS" ] && echo "No Transit Gateways found" && exit 0

# Route Tables & Attachments
aws ec2 describe-transit-gateway-route-tables $PROFILE_ARG --region "$REGION" --output json > "$OUTPUT_DIR/tgw-route-tables.json"
aws ec2 describe-transit-gateway-attachments $PROFILE_ARG --region "$REGION" --output json > "$OUTPUT_DIR/tgw-attachments.json"
aws ec2 describe-route-tables $PROFILE_ARG --region "$REGION" --output json > "$OUTPUT_DIR/route-tables.json"

# Get detailed VPC attachment information including subnet_ids
VPC_ATTACHMENT_IDS=$(aws ec2 describe-transit-gateway-attachments $PROFILE_ARG --region "$REGION" \
  --filters "Name=resource-type,Values=vpc" \
  --query 'TransitGatewayAttachments[*].TransitGatewayAttachmentId' --output text)

for ATT_ID in $VPC_ATTACHMENT_IDS; do
  aws ec2 describe-transit-gateway-vpc-attachments $PROFILE_ARG --region "$REGION" \
    --transit-gateway-attachment-ids "$ATT_ID" --output json > "$OUTPUT_DIR/tgw-vpc-attachment-$ATT_ID.json"
done

# Get peering attachments (for inter-region peering)
PEERING_IDS=$(aws ec2 describe-transit-gateway-attachments $PROFILE_ARG --region "$REGION" \
  --filters "Name=resource-type,Values=peering" \
  --query 'TransitGatewayAttachments[*].TransitGatewayAttachmentId' --output text)

for PEER_ID in $PEERING_IDS; do
  aws ec2 describe-transit-gateway-peering-attachments $PROFILE_ARG --region "$REGION" \
    --transit-gateway-attachment-ids "$PEER_ID" --output json > "$OUTPUT_DIR/tgw-peering-attachment-$PEER_ID.json"
done

# Get VPN attachments
VPN_ATTACHMENT_IDS=$(aws ec2 describe-transit-gateway-attachments $PROFILE_ARG --region "$REGION" \
  --filters "Name=resource-type,Values=vpn" \
  --query 'TransitGatewayAttachments[*].TransitGatewayAttachmentId' --output text)

for VPN_ID in $VPN_ATTACHMENT_IDS; do
  # Get VPN connection details
  VPN_CONN_ID=$(aws ec2 describe-transit-gateway-attachments $PROFILE_ARG --region "$REGION" \
    --transit-gateway-attachment-ids "$VPN_ID" \
    --query 'TransitGatewayAttachments[0].ResourceId' --output text)

  if [ -n "$VPN_CONN_ID" ]; then
    aws ec2 describe-vpn-connections $PROFILE_ARG --region "$REGION" \
      --vpn-connection-ids "$VPN_CONN_ID" --output json > "$OUTPUT_DIR/tgw-vpn-attachment-$VPN_ID.json"
  fi
done

# Get Direct Connect Gateway attachments
DX_ATTACHMENT_IDS=$(aws ec2 describe-transit-gateway-attachments $PROFILE_ARG --region "$REGION" \
  --filters "Name=resource-type,Values=direct-connect-gateway" \
  --query 'TransitGatewayAttachments[*].TransitGatewayAttachmentId' --output text)

for DX_ID in $DX_ATTACHMENT_IDS; do
  # Get Direct Connect Gateway details
  DX_GW_ID=$(aws ec2 describe-transit-gateway-attachments $PROFILE_ARG --region "$REGION" \
    --transit-gateway-attachment-ids "$DX_ID" \
    --query 'TransitGatewayAttachments[0].ResourceId' --output text)

  if [ -n "$DX_GW_ID" ]; then
    aws directconnect describe-direct-connect-gateways $PROFILE_ARG --region "$REGION" \
      --direct-connect-gateway-id "$DX_GW_ID" --output json > "$OUTPUT_DIR/tgw-dx-attachment-$DX_ID.json" 2>/dev/null || true
  fi
done

# Associations & Propagations
for TGW_ID in $TGW_IDS; do
  RT_IDS=$(aws ec2 describe-transit-gateway-route-tables $PROFILE_ARG --region "$REGION" \
    --filters "Name=transit-gateway-id,Values=$TGW_ID" \
    --query 'TransitGatewayRouteTables[*].TransitGatewayRouteTableId' --output text)

  for RT_ID in $RT_IDS; do
    aws ec2 get-transit-gateway-route-table-associations $PROFILE_ARG --region "$REGION" \
      --transit-gateway-route-table-id "$RT_ID" --output json > "$OUTPUT_DIR/tgw-rt-associations-$RT_ID.json"
    aws ec2 get-transit-gateway-route-table-propagations $PROFILE_ARG --region "$REGION" \
      --transit-gateway-route-table-id "$RT_ID" --output json > "$OUTPUT_DIR/tgw-rt-propagations-$RT_ID.json"
    aws ec2 search-transit-gateway-routes $PROFILE_ARG --region "$REGION" \
      --transit-gateway-route-table-id "$RT_ID" \
      --filters "Name=state,Values=active,blackhole" --output json > "$OUTPUT_DIR/tgw-rt-routes-$RT_ID.json"
  done
done

TGW_COUNT=$(jq '.TransitGateways | length' "$OUTPUT_DIR/transit-gateways.json")
RT_COUNT=$(jq '.TransitGatewayRouteTables | length' "$OUTPUT_DIR/tgw-route-tables.json")
ATT_COUNT=$(jq '.TransitGatewayAttachments | length' "$OUTPUT_DIR/tgw-attachments.json")
VPN_COUNT=$(echo "$VPN_ATTACHMENT_IDS" | wc -w)
DX_COUNT=$(echo "$DX_ATTACHMENT_IDS" | wc -w)

echo "✓ Completed: $OUTPUT_DIR"
echo "  TGW: $TGW_COUNT, Route Tables: $RT_COUNT, Attachments: $ATT_COUNT (VPC+VPN:$VPN_COUNT+DX:$DX_COUNT)"
