# ─── OPENSEARCH (Free Tier: t3.small.search, 10GB EBS, 750h/mês) ─────────────

resource "aws_opensearch_domain" "main" {
  domain_name    = "${var.project_name}-${var.environment}"
  engine_version = "OpenSearch_2.13"

  cluster_config {
    instance_type  = var.opensearch_instance_type # t3.small.search — free tier
    instance_count = 1
  }

  ebs_options {
    ebs_enabled = true
    volume_type = "gp3"
    volume_size = var.opensearch_volume_size # 10 GB — free tier
  }

  encrypt_at_rest {
    enabled = true
  }

  node_to_node_encryption {
    enabled = true
  }

  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }

  advanced_security_options {
    enabled                        = true
    anonymous_auth_enabled         = false
    internal_user_database_enabled = true

    master_user_options {
      master_user_name     = "admin"
      master_user_password = random_password.opensearch_master.result
    }
  }

  access_policies = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { AWS = aws_iam_role.lambda_exec.arn }
        Action    = "es:*"
        Resource  = "arn:aws:es:${var.aws_region}:${data.aws_caller_identity.current.account_id}:domain/${var.project_name}-${var.environment}/*"
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-opensearch"
    FreeTier    = "true"
    CostControl = "destroy-when-not-in-use"
  }

  lifecycle {
    ignore_changes = [access_policies]
  }
}

resource "random_password" "opensearch_master" {
  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Salva credenciais no SSM pra Lambda usar
resource "aws_ssm_parameter" "opensearch_password" {
  name  = "/${var.project_name}/${var.environment}/opensearch/password"
  type  = "SecureString"
  value = random_password.opensearch_master.result
}

resource "aws_ssm_parameter" "opensearch_endpoint" {
  name  = "/${var.project_name}/${var.environment}/opensearch/endpoint"
  type  = "String"
  value = "https://${aws_opensearch_domain.main.endpoint}"
}
