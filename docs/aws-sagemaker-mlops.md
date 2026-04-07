# AWS SageMaker MLOps Guide

## Overview

Amazon SageMaker is AWS's fully managed platform for building, training, and deploying
machine learning models at scale. It provides an integrated set of tools that cover the
entire ML lifecycle, making it the primary platform for MLOps on AWS.

## SageMaker Pipelines

SageMaker Pipelines is a purpose-built CI/CD service for ML workflows.
It enables teams to automate and standardize the end-to-end ML lifecycle.

### Pipeline Steps

**Processing Step**: Data preprocessing, feature engineering, model evaluation.
Uses SageMaker Processing Jobs under the hood, which spin up managed EC2 instances,
run your script, and terminate automatically — you pay only for compute time used.

**Training Step**: Model training with automatic experiment tracking via SageMaker Experiments.
Supports distributed training across multiple instances for large models.

**Condition Step**: Branching logic based on metrics (e.g., only deploy if accuracy > 0.90).
Critical for preventing degraded models from reaching production.

**Model Step**: Registers trained model in SageMaker Model Registry with metadata,
approval status (PendingManualApproval or Approved), and lineage tracking.

**Deploy Step**: Deploys approved model to a SageMaker Endpoint with specified instance type.

### Example Pipeline Pattern

```python
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.steps import ProcessingStep, TrainingStep, ConditionStep

pipeline = Pipeline(
    name="mlops-training-pipeline",
    steps=[preprocessing_step, training_step, evaluation_step, condition_step],
    sagemaker_session=session,
)
pipeline.upsert(role_arn=role)
pipeline.start()
```

## SageMaker Model Monitor

Model Monitor continuously monitors ML models in production to detect data drift,
model quality degradation, bias drift, and feature attribution drift.

### Monitor Types

**Data Quality Monitor**: Detects statistical changes in input features.
Compares production data distribution against a baseline computed from training data.
Alerts when distributions diverge beyond configured thresholds.

**Model Quality Monitor**: Tracks prediction quality over time.
Requires ground truth labels to be available (with delay) for comparison against predictions.

**Bias Drift Monitor**: Detects changes in model fairness metrics.
Uses Clarify under the hood to compute fairness metrics like disparate impact.

**Feature Attribution Drift Monitor**: Monitors changes in SHAP feature importance values.
Alerts when the model's decision-making logic changes unexpectedly.

### Monitor Configuration

```python
from sagemaker.model_monitor import DefaultModelMonitor

monitor = DefaultModelMonitor(
    role=role,
    instance_count=1,
    instance_type="ml.m5.xlarge",
    volume_size_in_gb=20,
    max_runtime_in_seconds=3600,
)

monitor.create_monitoring_schedule(
    monitor_schedule_name="hourly-data-quality",
    endpoint_input=endpoint_name,
    output_s3_uri=s3_report_path,
    statistics=baseline_statistics,
    constraints=baseline_constraints,
    schedule_cron_expression="cron(0 * ? * * *)",
)
```

## SageMaker Feature Store

SageMaker Feature Store provides a centralized repository for ML features,
solving the critical training-serving skew problem.

### Offline vs Online Store

The **offline store** persists features to S3 in Parquet format, partitioned by event time.
It supports time-travel queries to retrieve feature values as they existed at any point in time.
This is essential for preventing data leakage during model training.

The **online store** provides single-digit millisecond reads via a managed key-value store.
It always returns the latest feature value for a given record, suitable for real-time inference.

### Time-Travel Queries

A critical feature of the offline store is point-in-time correct joins:

```python
from sagemaker.feature_store.feature_group import FeatureGroup

feature_group = FeatureGroup(name="customer-features", sagemaker_session=session)

# Retrieve features as they existed at training time — prevents data leakage
training_data = feature_group.as_hive_ddl()
```

## SageMaker Endpoints and Autoscaling

### Endpoint Variants and A/B Testing

SageMaker supports multiple production variants per endpoint, enabling A/B testing
and canary deployments without downtime:

```python
production_variants = [
    {
        "VariantName": "model-v1",
        "ModelName": "my-model-v1",
        "InitialInstanceCount": 2,
        "InstanceType": "ml.m5.large",
        "InitialVariantWeight": 0.9,  # 90% do tráfego
    },
    {
        "VariantName": "model-v2-canary",
        "ModelName": "my-model-v2",
        "InitialInstanceCount": 1,
        "InstanceType": "ml.m5.large",
        "InitialVariantWeight": 0.1,  # 10% do tráfego
    },
]
```

### Auto Scaling Configuration

```python
# Target tracking: mantém utilização de CPU em 70%
scaling_config = {
    "TargetValue": 70.0,
    "PredefinedMetricSpecification": {
        "PredefinedMetricType": "SageMakerVariantInvocationsPerInstance"
    },
}
```

## Cost Optimization in SageMaker MLOps

### Managed Spot Training
Training jobs can use EC2 Spot instances, reducing costs by up to 90%.
SageMaker handles Spot interruptions automatically with checkpointing:

```python
estimator = Estimator(
    use_spot_instances=True,
    max_wait=7200,           # tempo máximo incluindo espera por Spot
    max_run=3600,            # tempo máximo de execução
    checkpoint_s3_uri=f"s3://{bucket}/checkpoints",
)
```

### Inference Savings Plans
For predictable inference workloads, SageMaker Savings Plans offer up to 64% discount
compared to on-demand pricing with 1-year or 3-year commitments.

### Serverless Inference
For intermittent workloads, SageMaker Serverless Inference eliminates idle costs:
- Scales to zero when not in use
- Responds in milliseconds when invoked (with cold start caveat)
- Ideal for portfólio demos and low-traffic APIs

## MLflow Integration with SageMaker

MLflow is the standard open-source experiment tracking platform,
and AWS provides managed MLflow on SageMaker:

```python
import mlflow
import sagemaker

# Configura MLflow tracking server no SageMaker
mlflow.set_tracking_uri(sagemaker_mlflow_arn)
mlflow.set_experiment("rag-mlops-experiment")

with mlflow.start_run():
    mlflow.log_param("chunk_size", 512)
    mlflow.log_param("embedding_model", "amazon.titan-embed-text-v2:0")
    mlflow.log_metric("retrieval_precision_at_5", 0.87)
    mlflow.log_metric("answer_relevance_score", 0.91)
    mlflow.sklearn.log_model(model, "rag-model")
```
