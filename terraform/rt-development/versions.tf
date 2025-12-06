terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }

  # Uncomment and configure for remote state storage
  # backend "s3" {
  #   bucket = "my-terraform-state"
  #   key    = "tgw/{account_id}/{region}/rt-{name}/terraform.tfstate"
  #   region = "ap-northeast-1"
  # }
}

provider "aws" {
  region = local.region
}
