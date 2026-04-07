terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }

  # Descomente para usar S3 backend em produção
  # backend "s3" {
  #   bucket         = "rag-mlops-terraform-state"
  #   key            = "rag-mlops/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "rag-mlops-terraform-lock"
  #   encrypt        = true
  # }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile

  default_tags {
    tags = {
      Project     = "rag-mlops-aws"
      Environment = var.environment
      ManagedBy   = "terraform"
      Owner       = "rafa-portfolio"
    }
  }
}

# ─── DATA SOURCES ─────────────────────────────────────────────────────────────

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
