variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS CLI profile"
  type        = string
  default     = "default"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name prefix for all resources"
  type        = string
  default     = "rag-mlops"
}

variable "opensearch_instance_type" {
  description = "OpenSearch instance type (t3.small.search = free tier eligible)"
  type        = string
  default     = "t3.small.search"
}

variable "opensearch_volume_size" {
  description = "OpenSearch EBS volume size in GB (10 GB = free tier)"
  type        = number
  default     = 10
}

variable "bedrock_embedding_model" {
  description = "Bedrock model ID for embeddings"
  type        = string
  default     = "amazon.titan-embed-text-v2:0"
}

variable "bedrock_llm_model" {
  description = "Bedrock model ID for text generation"
  type        = string
  default     = "anthropic.claude-3-haiku-20240307-v1:0"
}

variable "chunk_size" {
  description = "Document chunk size in tokens"
  type        = number
  default     = 512
}

variable "chunk_overlap" {
  description = "Document chunk overlap in tokens"
  type        = number
  default     = 50
}

variable "top_k_results" {
  description = "Number of chunks to retrieve per query"
  type        = number
  default     = 5
}

variable "alert_email" {
  description = "Email para alertas de custo AWS Budget"
  type        = string
  default     = ""
}
