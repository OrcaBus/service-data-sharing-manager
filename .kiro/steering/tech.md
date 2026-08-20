# Tech Stack

## Infrastructure (TypeScript)

- **CDK**: AWS CDK v2 (`aws-cdk-lib ^2.259.0`) with `@orcabus/platform-cdk-constructs`
- **Language**: TypeScript (ES2020 target, strict mode)
- **Package Manager**: pnpm 11 (via Corepack, lockfile enforced with `--frozen-lockfile`)
- **Node**: v22
- **Test Framework**: Jest with ts-jest (`test/` folder, cdk-nag compliance tests)
- **Linting**: ESLint v10 + typescript-eslint
- **Formatting**: Prettier
- **Pre-commit**: pre-commit hooks (large files, YAML, secrets detection, eslint, prettier)

## Application Code (Python)

- **Runtime**: Python 3.14
- **API Framework**: FastAPI + Mangum (Lambda adapter)
- **ORM / DB**: Dyntastic (DynamoDB), Pydantic v2
- **Lambda Layer**: Managed with Poetry (`app/layers/data_sharing_tools_layer/`)
- **ECS Tasks**: Dockerized Python tools (e.g. report generation)
- **Step Functions**: ASL JSON templates in `app/step-functions-templates/`

## Common Commands

```bash
# Install all dependencies (Node + pnpm)
make install

# Run linting and formatting checks
make check

# Auto-fix lint/format issues
make fix

# Run tests (compiles TypeScript, then runs Jest)
make test

# CDK commands (via pnpm scripts)
pnpm cdk-stateless list        # List stateless stacks
pnpm cdk-stateless synth       # Synthesize stateless stacks
pnpm cdk-stateful list         # List stateful stacks
pnpm cdk-stateful synth        # Synthesize stateful stacks
```

## Key Dependencies

| Layer        | Package                            | Purpose                                                  |
| ------------ | ---------------------------------- | -------------------------------------------------------- |
| CDK          | `@orcabus/platform-cdk-constructs` | Shared OrcaBus CDK constructs (pipelines, API GW config) |
| CDK          | `cdk-nag`                          | CDK compliance / best-practice checks                    |
| Python API   | `fastapi`, `mangum`                | HTTP API served via Lambda                               |
| Python API   | `dyntastic`                        | DynamoDB ORM                                             |
| Python API   | `ulid-py`                          | ULID generation for package/push IDs                     |
| Python Layer | `data_sharing_tools`               | Shared utilities across lambdas                          |
