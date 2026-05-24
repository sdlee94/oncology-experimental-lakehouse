provider "aws" {
  region = "us-east-1"
}

# S3 bucket for lakehouse data
resource "aws_s3_bucket" "oncology_experimental_lakehouse" {
  bucket = "oncology-experimental-lakehouse"

  lifecycle {
    prevent_destroy = true
  }
}

# Athena databases
resource "aws_glue_catalog_database" "lakehouse_raw" {
  name        = "lakehouse_raw"
  description = "Raw layer database for oncology experimental lakehouse"
}

# IAM role for Glue crawler
resource "aws_iam_role" "glue_crawler_role" {
  name = "oncology-lakehouse-glue-crawler-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
      }
    ]
  })
}

# IAM policy for Glue crawler
resource "aws_iam_role_policy" "glue_crawler_policy" {
  name = "oncology-lakehouse-glue-crawler-policy"
  role = aws_iam_role.glue_crawler_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          "${aws_s3_bucket.oncology_experimental_lakehouse.arn}",
          "${aws_s3_bucket.oncology_experimental_lakehouse.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "glue:*"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Glue crawler for raw experiments
resource "aws_glue_crawler" "raw_experiments" {
  name          = "raw_experiments"
  database_name = aws_glue_catalog_database.lakehouse_raw.name
  role          = aws_iam_role.glue_crawler_role.arn

  table_prefix = "raw_"

  s3_target {
    path = "s3://${aws_s3_bucket.oncology_experimental_lakehouse.bucket}/raw/experiments/"
  }

  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }

  configuration = jsonencode({
    Version = 1.0
    Grouping = {
      TableGroupingPolicy = "CombineCompatibleSchemas"
      TableLevelConfiguration = 3
    }
    CreatePartitionIndex = false
  })
}

# Glue crawler for raw samples
resource "aws_glue_crawler" "raw_samples" {
  name          = "raw_samples"
  database_name = aws_glue_catalog_database.lakehouse_raw.name
  role          = aws_iam_role.glue_crawler_role.arn

  table_prefix = "raw_"

  s3_target {
    path = "s3://${aws_s3_bucket.oncology_experimental_lakehouse.bucket}/raw/samples/"
  }

  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }

  configuration = jsonencode({
    Version = 1.0
    Grouping = {
      TableGroupingPolicy = "CombineCompatibleSchemas"
      TableLevelConfiguration = 3
    }
    CreatePartitionIndex = false
  })
}

# Glue crawler for raw stocks
resource "aws_glue_crawler" "raw_stocks" {
  name          = "raw_stocks"
  database_name = aws_glue_catalog_database.lakehouse_raw.name
  role          = aws_iam_role.glue_crawler_role.arn

  table_prefix = "raw_"

  s3_target {
    path = "s3://${aws_s3_bucket.oncology_experimental_lakehouse.bucket}/raw/stocks/"
  }

  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }

  configuration = jsonencode({
    Version = 1.0
    Grouping = {
      TableGroupingPolicy = "CombineCompatibleSchemas"
      TableLevelConfiguration = 3
    }
    CreatePartitionIndex = false
  })
}

# Glue crawler for raw screening results
resource "aws_glue_crawler" "raw_screening_results" {
  name          = "raw_screening_results"
  database_name = aws_glue_catalog_database.lakehouse_raw.name
  role          = aws_iam_role.glue_crawler_role.arn

  table_prefix = "raw_"

  s3_target {
    path = "s3://${aws_s3_bucket.oncology_experimental_lakehouse.bucket}/raw/screening_results/"
  }

  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }

  configuration = jsonencode({
    Version = 1.0
    Grouping = {
      TableGroupingPolicy = "CombineCompatibleSchemas"
      TableLevelConfiguration = 3
    }
    CreatePartitionIndex = false
  })
}