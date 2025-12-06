# Reference Transit Gateway and Attachments
#
# For local backend (default):
#   Use relative path to tgw directory
#
# For remote backend (S3, etc):
#   Update the backend and config blocks below to match your backend configuration
#   Example for S3:
#   backend = "s3"
#   config = {
#     bucket = "my-terraform-state"
#     key    = "tgw/{account_id}/{region}/tgw/terraform.tfstate"
#     region = "ap-northeast-1"
#   }
data "terraform_remote_state" "tgw" {
  backend = "local"

  config = {
    path = "../tgw/terraform.tfstate"
  }
}

locals {
  transit_gateway_id = data.terraform_remote_state.tgw.outputs.transit_gateway_id
  region             = data.terraform_remote_state.tgw.outputs.region
  common_tags        = data.terraform_remote_state.tgw.outputs.tags

  # Reference all attachments from tgw module
  vpc_attachment_ids        = try(data.terraform_remote_state.tgw.outputs.vpc_attachment_ids, {})
  peering_attachment_ids    = try(data.terraform_remote_state.tgw.outputs.peering_attachment_ids, {})
  vpn_attachment_ids        = try(data.terraform_remote_state.tgw.outputs.vpn_attachment_ids, {})
  dx_gateway_attachment_ids = try(data.terraform_remote_state.tgw.outputs.dx_gateway_attachment_ids, {})
}
