#!/bin/bash
set -euo pipefail

REGION="${AWS_REGION:-ap-northeast-1}"
OUTPUT_DIR="./output"
TERRAFORM_DIR="./terraform"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

log() { echo "[$(date +%H:%M:%S)] $1"; }

check_prerequisites() {
    log "Checking prerequisites..."
    command -v aws &>/dev/null || { echo "Error: AWS CLI not installed"; exit 1; }
    command -v python3 &>/dev/null || { echo "Error: Python 3 not installed"; exit 1; }
    command -v jq &>/dev/null || { echo "Error: jq not installed"; exit 1; }
    command -v terraform &>/dev/null || { echo "Error: Terraform not installed"; exit 1; }
    aws sts get-caller-identity &>/dev/null || { echo "Error: AWS credentials invalid"; exit 1; }
}

fetch_resources() {
    log "Fetching AWS resources..."
    cd "$PROJECT_ROOT" && AWS_REGION=$REGION OUTPUT_DIR=$OUTPUT_DIR "$SCRIPT_DIR/fetch_aws_resources.sh"
}

generate_terraform() {
    log "Generating Terraform code..."
    cd "$PROJECT_ROOT" && python3 "$SCRIPT_DIR/generate_terraform.py" \
        --input-dir "$OUTPUT_DIR" --output-dir "$TERRAFORM_DIR" --region "$REGION"
}

init_terraform() {
    log "Initializing Terraform..."
    cd "$TERRAFORM_DIR" && terraform init
}

generate_import_script() {
    log "Generating import script..."
    cd "$PROJECT_ROOT" && python3 "$SCRIPT_DIR/generate_import_commands.py" \
        --input-dir "$OUTPUT_DIR" --terraform-dir "$TERRAFORM_DIR" --output "$SCRIPT_DIR/import.sh"
}

execute_import() {
    log "Importing resources (Ctrl+C to cancel)..."
    sleep 2
    [ -f "$SCRIPT_DIR/import.sh" ] || { echo "Error: import.sh not found"; exit 1; }
    "$SCRIPT_DIR/import.sh"
}

verify_state() {
    log "Verifying with terraform plan..."
    cd "$TERRAFORM_DIR" && terraform plan
}

main() {
    SKIP_IMPORT=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-import) SKIP_IMPORT=true; shift ;;
            --region) REGION="$2"; shift 2 ;;
            --help) echo "Usage: $0 [--region REGION] [--skip-import]"; exit 0 ;;
            *) echo "Unknown option: $1"; exit 1 ;;
        esac
    done

    echo "=== Transit Gateway Terraform Importer ==="
    echo "Region: $REGION"
    echo ""

    check_prerequisites
    fetch_resources
    generate_terraform
    init_terraform
    generate_import_script

    if [ "$SKIP_IMPORT" = false ]; then
        execute_import
        verify_state
    fi

    log "Complete!"
}

main "$@"
