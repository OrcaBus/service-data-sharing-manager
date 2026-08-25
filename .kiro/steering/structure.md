# Project Structure

```
service-data-sharing-manager/
├── app/                          # Application code (Python)
│   ├── interface/                # FastAPI REST API
│   │   ├── data_sharing_api/     # API package
│   │   │   ├── api/v1/           # Versioned route handlers
│   │   │   ├── events/           # Event-driven handlers
│   │   │   ├── models/           # Pydantic / Dyntastic models
│   │   │   └── utils.py
│   │   ├── handler.py            # Lambda entry point (Mangum)
│   │   └── requirements.txt
│   ├── lambdas/                  # Individual Lambda functions (Python)
│   │   └── <name>_py/           # One folder per lambda, named with _py suffix
│   ├── layers/                   # Shared Lambda layers
│   │   └── data_sharing_tools_layer/  # Poetry-managed shared utilities
│   ├── ecs/tasks/                # ECS task definitions (Docker)
│   │   └── generate_data_summary_report/
│   └── step-functions-templates/ # ASL JSON Step Function definitions
├── infrastructure/               # CDK infrastructure code (TypeScript)
│   ├── stage/                    # Per-environment resource definitions
│   │   ├── config.ts             # Environment-specific configuration
│   │   ├── constants.ts          # Shared constant values
│   │   ├── interfaces.ts         # TypeScript interfaces for stack props
│   │   ├── stateful-application-stack.ts
│   │   ├── stateless-application-stack.ts
│   │   ├── api/                  # API Gateway constructs
│   │   ├── dynamodb/             # DynamoDB table constructs
│   │   ├── ecs/                  # ECS task constructs
│   │   ├── event-rules/          # EventBridge rule constructs
│   │   ├── event-targets/        # EventBridge target constructs
│   │   ├── lambdas/              # Lambda function constructs
│   │   ├── s3/                   # S3 bucket constructs
│   │   ├── secrets/              # Secrets Manager constructs
│   │   ├── ssm/                  # SSM Parameter Store constructs
│   │   ├── step-functions/       # Step Function constructs
│   │   └── utils/                # Infrastructure utility helpers
│   └── toolchain/                # CodePipeline stacks (toolchain account)
│       ├── stateful-stack.ts
│       └── stateless-stack.ts
├── bin/deploy.ts                 # CDK app entry point
├── test/                         # CDK compliance tests (Jest + cdk-nag)
├── scripts/                      # Utility scripts (e.g. CLI installer)
└── scratch/                      # Experimental / temporary files
```

## Conventions

- **Lambda naming**: Each lambda lives in `app/lambdas/<descriptive_name>_py/` containing a single Python handler file.
- **Infrastructure resource grouping**: Each AWS resource type has its own folder under `infrastructure/stage/` with an `index.ts` (construct) and `interfaces.ts` (props type).
- **Stateful vs Stateless split**: Resources are separated into stateful (DynamoDB, S3) and stateless (Lambda, Step Functions, API GW) stacks for safe independent deployment.
- **Step Functions**: Defined as ASL JSON templates in `app/step-functions-templates/`, referenced by CDK constructs.
- **Python shared code**: Common utilities live in the `data_sharing_tools_layer` Lambda layer, managed via Poetry.
- **API versioning**: Routes are versioned under `api/v1/`.
- **ESLint scope**: The root eslint config ignores `app/` — application Python code has its own linting.
