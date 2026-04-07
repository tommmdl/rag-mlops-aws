# MLOps Fundamentals

## What is MLOps?

MLOps (Machine Learning Operations) is a set of practices that combines Machine Learning,
DevOps, and Data Engineering to deploy and maintain ML models in production reliably and efficiently.
It addresses the unique challenges of operationalizing ML systems beyond traditional software.

## Core Principles

### Reproducibility
Every experiment, dataset version, and model artifact must be tracked and reproducible.
Tools like MLflow, DVC, and Neptune enable experiment tracking and dataset versioning.
Without reproducibility, debugging production issues becomes nearly impossible.

### Automation
The entire ML pipeline — from data ingestion to model serving — should be automated.
CI/CD pipelines for ML (using GitHub Actions, AWS CodePipeline, or Argo Workflows)
ensure consistent, repeatable deployments with minimal human intervention.

### Continuous Training (CT)
Unlike traditional software, ML models degrade over time due to data drift and concept drift.
Continuous Training pipelines automatically retrain models when performance drops below thresholds,
triggered by monitoring systems like AWS SageMaker Model Monitor or Evidently AI.

### Monitoring and Observability
Four types of monitoring are essential in MLOps:
1. Infrastructure metrics (CPU, memory, latency, throughput)
2. Data quality metrics (schema validation, statistical distributions)
3. Model performance metrics (accuracy, F1, AUC on production data)
4. Business metrics (revenue impact, conversion rate, user satisfaction)

## MLOps Maturity Levels

### Level 0 — Manual Process
- Data scientists manually train and deploy models
- No automation, no CI/CD
- Models are deployed as one-time scripts
- Suitable only for proof of concept

### Level 1 — ML Pipeline Automation
- Automated training pipelines
- Feature stores for reusable features
- Model registry for versioning (MLflow, SageMaker Model Registry)
- Automated retraining triggers based on data drift detection

### Level 2 — CI/CD Pipeline Automation
- Full CI/CD for ML pipelines themselves
- Automated testing: unit tests, integration tests, model validation tests
- A/B testing and canary deployments for model releases
- Complete experiment tracking and lineage

## Feature Stores

A Feature Store is a centralized repository for storing, sharing, and serving ML features.
It solves the training-serving skew problem by ensuring features computed at training time
are identical to those served in production.

Key components:
- **Offline store**: Historical features for training (typically S3 + Glue or Delta Lake)
- **Online store**: Low-latency serving for real-time inference (DynamoDB, Redis, Feast)
- **Feature transformation**: Consistent logic applied in both offline and online contexts

AWS SageMaker Feature Store is a managed feature store that supports both offline (S3) and
online (DynamoDB-backed) storage with millisecond retrieval latency.

## Model Serving Patterns

### Real-time Inference
Best for: user-facing applications requiring immediate responses
Latency: < 100ms typically required
Tools: AWS SageMaker Endpoints, BentoML, TorchServe, FastAPI + Lambda

### Batch Inference
Best for: overnight predictions on large datasets
Latency: hours acceptable
Tools: AWS SageMaker Batch Transform, AWS Glue, Apache Spark

### Streaming Inference
Best for: event-driven predictions on data streams
Tools: AWS Kinesis + Lambda, Apache Kafka + Flink

## Data Drift and Concept Drift

**Data Drift** (covariate shift): The statistical distribution of input features changes over time.
Example: A fraud detection model trained in 2022 may fail in 2024 because spending patterns changed.

**Concept Drift**: The relationship between inputs and outputs changes.
Example: Customer churn predictors trained before a competitor launch become invalid after.

Detection methods:
- Population Stability Index (PSI)
- Kolmogorov-Smirnov test
- Jensen-Shannon divergence
- CUSUM (Cumulative Sum Control Chart)

## CI/CD for Machine Learning

A robust ML CI/CD pipeline includes:

1. **Data validation**: Great Expectations or Deequ to validate input data schema and quality
2. **Model training**: Automated training with hyperparameter tuning (Optuna, Ray Tune)
3. **Model evaluation**: Automated comparison against baseline model on holdout dataset
4. **Model registry**: Automatic registration with metadata if evaluation passes thresholds
5. **Deployment**: Blue/green or canary deployment to production endpoint
6. **Integration tests**: End-to-end tests verifying the deployed model responds correctly
7. **Monitoring setup**: Automatic configuration of monitoring dashboards and alerts

## Infrastructure as Code for MLOps

Terraform is the standard for provisioning ML infrastructure:
- SageMaker training instances
- Feature store tables
- Model endpoints with auto-scaling
- S3 buckets for artifacts
- IAM roles and policies

Key principle: All infrastructure must be version-controlled and reproducible.
Never provision ML infrastructure manually through the console.
