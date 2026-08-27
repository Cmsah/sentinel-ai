# --- Application ---
output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.cluster_name
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = module.ecs.service_name
}

output "app_url" {
  description = "Application URL (via ALB)"
  value       = module.ecs.app_url
}

# --- Database ---
# TODO: Uncomment once modules/rds/ is implemented
# output "rds_endpoint" {
#   description = "RDS endpoint"
#   value       = module.rds.endpoint
#   sensitive   = true
# }

# output "database_url" {
#   description = "PostgreSQL connection URL"
#   value       = module.rds.database_url
#   sensitive   = true
# }

# --- Redis ---
# TODO: Uncomment once modules/elasticache/ is implemented
# output "redis_endpoint" {
#   description = "ElastiCache Redis endpoint"
#   value       = module.elasticache.endpoint
#   sensitive   = true
# }

# --- VPC ---
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnet_ids
}
