variable "aws_region" {
  default = "us-east-1"
}

variable "account_id" {
  default = "971983845745"
}

variable "project" {
  default = "sports-analytics"
}

variable "environment" {
  default = "dev"
}

variable "sportradar_api_key" {
  description = "SportsRadar API key"
  sensitive   = true
}

variable "odds_api_key" {
  description = "The Odds API key"
  sensitive   = true
}

variable "groq_api_key" {
  description = "Groq API key for Llama AI"
  sensitive   = true
}
