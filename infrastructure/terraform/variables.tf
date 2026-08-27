# --- General ---
variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "sentinel-ai"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be development, staging, or production."
  }
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

# --- VPC ---
variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

# --- ECS ---
variable "container_image" {
  description = "Docker image for the Sentinel AI app"
  type        = string
  default     = "sentinel-ai:latest"
}

variable "ecs_desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 2
}

variable "ecs_cpu" {
  description = "CPU units for ECS task (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "ecs_memory" {
  description = "Memory (MiB) for ECS task"
  type        = number
  default     = 2048
}

# --- RDS ---
variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "rds_allocated_storage" {
  description = "RDS allocated storage (GB)"
  type        = number
  default     = 20
}

variable "database_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "sentinel"
}

variable "database_username" {
  description = "PostgreSQL master username"
  type        = string
  default     = "sentinel"
}

# --- Redis ---
variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.micro"
}

# --- Kafka ---
variable "kafka_brokers" {
  description = "Kafka broker addresses (comma-separated)"
  type        = string
  default     = ""
}

# --- Placeholder for RDS/ElastiCache (until modules are created) ---
variable "database_url_placeholder" {
  description = "PostgreSQL connection URL (replace with module.rds.database_url once RDS module exists)"
  type        = string
  default     = "postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentinel"
  sensitive   = true
}

variable "redis_url_placeholder" {
  description = "Redis connection URL (replace with module.elasticache.redis_url once module exists)"
  type        = string
  default     = "redis://localhost:6379/0"
  sensitive   = true
}
