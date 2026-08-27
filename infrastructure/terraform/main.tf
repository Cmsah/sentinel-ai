# ============================================================
# Sentinel AI — Terraform Configuration (AWS)
# ============================================================
# Provisions: VPC, ECS Fargate, RDS PostgreSQL, ElastiCache Redis
#
# Usage:
#   terraform init
#   terraform plan
#   terraform apply
# ============================================================

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# --- VPC ---
module "vpc" {
  source = "./modules/vpc"

  project_name = var.project_name
  environment  = var.environment
  vpc_cidr     = var.vpc_cidr
}

# --- ECS Fargate ---
module "ecs" {
  source = "./modules/ecs"

  project_name       = var.project_name
  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  public_subnet_ids  = module.vpc.public_subnet_ids
  container_image    = var.container_image
  container_port     = 8000
  desired_count      = var.ecs_desired_count
  cpu                = var.ecs_cpu
  memory             = var.ecs_memory

  database_url = var.database_url_placeholder
  redis_url    = var.redis_url_placeholder
  kafka_brokers = var.kafka_brokers
}

# --- RDS PostgreSQL ---
# TODO: Create modules/rds/ with RDS instance, security group, and subnet group
# module "rds" {
#   source = "./modules/rds"
#   project_name       = var.project_name
#   environment        = var.environment
#   vpc_id             = module.vpc.vpc_id
#   private_subnet_ids = module.vpc.private_subnet_ids
#   allowed_security_group_ids = [module.ecs.security_group_id]
#   instance_class    = var.rds_instance_class
#   allocated_storage = var.rds_allocated_storage
#   database_name     = var.database_name
#   master_username   = var.database_username
# }

# --- ElastiCache Redis ---
# TODO: Create modules/elasticache/ with Redis cluster, security group, and subnet group
# module "elasticache" {
#   source = "./modules/elasticache"
#   project_name       = var.project_name
#   environment        = var.environment
#   vpc_id             = module.vpc.vpc_id
#   private_subnet_ids = module.vpc.private_subnet_ids
#   allowed_security_group_ids = [module.ecs.security_group_id]
#   node_type = var.redis_node_type
# }
