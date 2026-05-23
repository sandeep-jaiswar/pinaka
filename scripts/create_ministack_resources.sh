#!/usr/bin/env bash
set -euo pipefail

AWS_ENDPOINT="${AWS_ENDPOINT:-http://localhost:4566}"
AWS_REGION="${AWS_REGION:-ap-south-1}"

export AWS_ACCESS_KEY_ID="test"
export AWS_SECRET_ACCESS_KEY="test"
export AWS_DEFAULT_REGION="${AWS_REGION}"

aws_cmd() {
  if command -v aws >/dev/null 2>&1; then
    aws --endpoint-url="${AWS_ENDPOINT}" "$@"
    return
  fi

  docker exec pinaka_ministack awslocal "$@"
}

echo "Creating S3 buckets in MiniStack at ${AWS_ENDPOINT}"
aws_cmd s3 mb s3://pinaka-raw || true
aws_cmd s3 mb s3://pinaka-bronze || true
aws_cmd s3 mb s3://pinaka-silver || true
aws_cmd s3 mb s3://pinaka-gold || true

echo "Creating SQS queues"
aws_cmd sqs create-queue --queue-name pinaka-ingest-jobs || true
aws_cmd sqs create-queue --queue-name pinaka-dlq || true

echo "MiniStack resources initialized"
