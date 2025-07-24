/*
Build the step functions

 */

// Imports
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import { Construct } from 'constructs';
import * as path from 'path';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as cdk from 'aws-cdk-lib';
import * as awsLogs from 'aws-cdk-lib/aws-logs';

// Local interfaces
import {
  SfnObject,
  SfnProps,
  SfnsProps,
  lambdasInStepFunctions,
  stepFunctionsNameList,
  stepFunctionsRequirementsMap,
  SfnPropsWithStateMachine,
} from './interfaces';
import { camelCaseToSnakeCase } from '../utils';
import {
  FASTQ_SYNC_DETAIL_TYPE,
  PACKAGING_LOOKUP_SECONDARY_INDEX_NAMES,
  S3_STEPS_COPY_PREFIX,
  SFN_PREFIX,
  STACK_SOURCE,
  STEP_FUNCTIONS_DIR,
} from '../constants';
import { NagSuppressions } from 'cdk-nag';
import { LogLevel, StateMachineType } from 'aws-cdk-lib/aws-stepfunctions';
import { RetentionDays } from 'aws-cdk-lib/aws-logs';

/** Step Function stuff */
function createStateMachineDefinitionSubstitutions(props: SfnProps): {
  [key: string]: string;
} {
  const definitionSubstitutions: { [key: string]: string } = {};
  const lambdaFunctionNamesInSfn = lambdasInStepFunctions[props.stateMachineName];
  const lambdaFunctions = props.lambdaObjects.filter((lambdaObject) =>
    lambdaFunctionNamesInSfn.includes(lambdaObject.lambdaName)
  );

  /* Substitute lambdas in the state machine definition */
  for (const lambdaObject of lambdaFunctions) {
    const sfnSubtitutionKey = `__${camelCaseToSnakeCase(lambdaObject.lambdaName)}_lambda_function_arn__`;
    definitionSubstitutions[sfnSubtitutionKey] =
      lambdaObject.lambdaFunction.currentVersion.functionArn;
  }

  // Add packaging lookup table bucket
  definitionSubstitutions['__dynamodb_table_name__'] = props.packagingLookupTable.tableName;

  // Add packaging bucket
  definitionSubstitutions['__sharing_bucket__'] = props.packagingBucket.bucketName;

  // Event stuff
  definitionSubstitutions['__stack_source__'] = STACK_SOURCE;
  definitionSubstitutions['__event_bus_name__'] = props.eventBusObject.eventBusName;
  definitionSubstitutions['__fastq_sync_detail_type__'] = FASTQ_SYNC_DETAIL_TYPE;

  // Ecs stuff
  definitionSubstitutions['__generate_data_package_report_container_name__'] =
    props.dataReportingEcsObject.containerDefinition.containerName;
  definitionSubstitutions['__security_group__'] =
    props.dataReportingEcsObject.securityGroup.securityGroupId;
  definitionSubstitutions['__subnets__'] = props.dataReportingEcsObject.cluster.vpc.privateSubnets
    .map((subnet) => subnet.subnetId)
    .join(',');
  definitionSubstitutions['__generate_data_package_report_task_definition_arn__'] =
    props.dataReportingEcsObject.taskDefinition.taskDefinitionArn;
  definitionSubstitutions['__generate_data_package_report_cluster_arn__'] =
    props.dataReportingEcsObject.cluster.clusterArn;

  // S3 Steps Copy stuff
  definitionSubstitutions['__aws_s3_copy_steps_bucket__'] = props.s3StepsCopyBucket.bucketName;
  definitionSubstitutions['__aws_s3_copy_steps_prefix__'] = S3_STEPS_COPY_PREFIX;

  // Nested state machines
  for (const nestedSfnName of stepFunctionsNameList) {
    switch (nestedSfnName) {
      case 'pushS3Data': {
        definitionSubstitutions['__s3_data_push_sfn_arn__'] =
          `arn:aws:states:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:stateMachine:${SFN_PREFIX}-${nestedSfnName}`;
        break;
      }
      case 'pushIcav2Data': {
        definitionSubstitutions['__icav2_data_push_sfn_arn__'] =
          `arn:aws:states:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:stateMachine:${SFN_PREFIX}-${nestedSfnName}`;
        break;
      }
    }
  }

  // Nested state machine is just part of our props
  definitionSubstitutions['__aws_s3_steps_copy_sfn_arn__'] = props.s3StepsCopySfn.stateMachineArn;

  return definitionSubstitutions;
}

function wireUpStateMachinePermissions(scope: Construct, props: SfnPropsWithStateMachine): void {
  /* Wire up lambda permissions */
  const sfnRequirements = stepFunctionsRequirementsMap[props.stateMachineName];

  const lambdaFunctionNamesInSfn = lambdasInStepFunctions[props.stateMachineName];
  const lambdaFunctions = props.lambdaObjects.filter((lambdaObject) =>
    lambdaFunctionNamesInSfn.includes(lambdaObject.lambdaName)
  );

  /* Allow the state machine to invoke the lambda function */
  for (const lambdaObject of lambdaFunctions) {
    lambdaObject.lambdaFunction.currentVersion.grantInvoke(props.stateMachineObj);
  }

  /* Sfn Requirements */
  // needsEventPutPermissions
  // needsEcsPermissions
  // needsDbRwPermissions
  // needsDbQueryPermissions
  // needsNestedSfnPermissions

  // Express Step functions will have * on log Permissions
  if (sfnRequirements.isExpressSfn) {
    NagSuppressions.addResourceSuppressions(
      props.stateMachineObj,
      [
        {
          id: 'AwsSolutions-IAM5',
          reason: 'Need ability to write log files',
        },
      ],
      true
    );
  }

  // Grant event bus permissions if needed
  if (sfnRequirements.needsEventPutPermissions) {
    props.eventBusObject.grantPutEventsTo(props.stateMachineObj);
  }

  // Grant ECS permissions if needed
  if (sfnRequirements.needsEcsPermissions) {
    props.dataReportingEcsObject.taskDefinition.grantRun(props.stateMachineObj);

    /* Grant the state machine access to monitor the tasks */
    props.stateMachineObj.addToRolePolicy(
      new iam.PolicyStatement({
        resources: [
          `arn:aws:events:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:rule/StepFunctionsGetEventsForECSTaskRule`,
        ],
        actions: ['events:PutTargets', 'events:PutRule', 'events:DescribeRule'],
      })
    );

    /* Will need cdk nag suppressions for this */
    NagSuppressions.addResourceSuppressions(
      props.stateMachineObj,
      [
        {
          id: 'AwsSolutions-IAM5',
          reason: 'Need ability to put targets and rules for ECS task monitoring',
        },
      ],
      true
    );
  }

  // Read / write access to the packaging lookup table
  if (sfnRequirements.needsDbRwPermissions) {
    props.packagingLookupTable.grantReadWriteData(props.stateMachineObj);
  }

  // Special case for query permissions
  if (sfnRequirements.needsDbQueryPermissions) {
    for (const indexName of PACKAGING_LOOKUP_SECONDARY_INDEX_NAMES) {
      props.stateMachineObj.addToRolePolicy(
        new iam.PolicyStatement({
          actions: ['dynamodb:Query'],
          resources: [
            `arn:aws:dynamodb:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:table/${props.packagingLookupTable.tableName}/index/${indexName}-index`,
          ],
        })
      );
    }
  }

  // SFNs with distributed maps require the following permissions
  if (sfnRequirements.needsDistributedMapPermissions) {
    // SFN requires permissions to execute itself
    // Because this steps execution uses a distributed map in its step function, we
    // have to wire up some extra permissions
    // Grant the state machine's role to execute itself
    // However we cannot just grant permission to the role as this will result in a circular dependency
    // between the state machine and the role
    // Instead we use the workaround here - https://github.com/aws/aws-cdk/issues/28820#issuecomment-1936010520
    const distributedMapPolicy = new iam.Policy(
      scope,
      `${props.stateMachineName}-distributed-map-policy`,
      {
        document: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              resources: [props.stateMachineObj.stateMachineArn],
              actions: ['states:StartExecution'],
            }),
            new iam.PolicyStatement({
              resources: [
                `arn:aws:states:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:execution:${props.stateMachineObj.stateMachineName}/*:*`,
              ],
              actions: ['states:RedriveExecution'],
            }),
          ],
        }),
      }
    );
    // Add the policy to the state machine's role
    props.stateMachineObj.role.attachInlinePolicy(distributedMapPolicy);
    // Oh and well also need to put in NagSuppressions because we just used a LOT of stars
    NagSuppressions.addResourceSuppressions(
      [distributedMapPolicy, props.stateMachineObj],
      [
        {
          id: 'AwsSolutions-IAM5',
          reason: 'We need to allow the state machine to execute itself and redrive executions',
        },
      ]
    );
  }

  // Nested SFN Permissions
  if (sfnRequirements.needsNestedSfnPermissions) {
    // For push data case
    if (props.stateMachineName === 'push') {
      for (const nestedSfnName of stepFunctionsNameList) {
        switch (nestedSfnName) {
          case 'pushS3Data':
          case 'pushIcav2Data': {
            props.stateMachineObj.addToRolePolicy(
              new iam.PolicyStatement({
                actions: ['states:StartExecution'],
                resources: [
                  `arn:aws:states:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:stateMachine:${SFN_PREFIX}-${nestedSfnName}`,
                ],
              })
            );
            break;
          }
        }
      }
    }

    // The s3 data push SFN needs access to the s3 steps copy state machine
    if (props.stateMachineName === 'pushS3Data') {
      props.s3StepsCopySfn.grantStartExecution(props.stateMachineObj);
    }

    // Because we run a nested state machine, we need to add the permissions to the state machine role
    // See https://stackoverflow.com/questions/60612853/nested-step-function-in-a-step-function-unknown-error-not-authorized-to-cr
    props.stateMachineObj.addToRolePolicy(
      new iam.PolicyStatement({
        resources: [
          `arn:aws:events:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:rule/StepFunctionsGetEventsForStepFunctionsExecutionRule`,
        ],
        actions: ['events:PutTargets', 'events:PutRule', 'events:DescribeRule'],
      })
    );
  }
}

function buildStepFunction(scope: Construct, props: SfnProps): SfnObject {
  const sfnNameToSnakeCase = camelCaseToSnakeCase(props.stateMachineName);
  const sfnRequirements = stepFunctionsRequirementsMap[props.stateMachineName];

  /* Create the state machine definition substitutions */
  const stateMachine = new sfn.StateMachine(scope, props.stateMachineName, {
    stateMachineName: `${SFN_PREFIX}-${props.stateMachineName}`,
    definitionBody: sfn.DefinitionBody.fromFile(
      path.join(STEP_FUNCTIONS_DIR, sfnNameToSnakeCase + `_sfn_template.asl.json`)
    ),
    definitionSubstitutions: createStateMachineDefinitionSubstitutions(props),
    stateMachineType: sfnRequirements.isExpressSfn
      ? StateMachineType.EXPRESS
      : StateMachineType.STANDARD,
    logs: sfnRequirements.isExpressSfn
      ? // Enable logging on the state machine
        {
          level: LogLevel.ALL,
          // Create a new log group for the state machine
          destination: new awsLogs.LogGroup(scope, `${props.stateMachineName}-logs`, {
            retention: RetentionDays.ONE_DAY,
          }),
          includeExecutionData: true,
        }
      : undefined,
  });

  /* Grant the state machine permissions */
  wireUpStateMachinePermissions(scope, {
    stateMachineObj: stateMachine,
    ...props,
  });

  /* Nag Suppressions */
  /* AwsSolutions-SF1 - We don't need ALL events to be logged */
  /* AwsSolutions-SF2 - We also don't need X-Ray tracing */
  NagSuppressions.addResourceSuppressions(
    stateMachine,
    [
      {
        id: 'AwsSolutions-SF1',
        reason: 'We do not need all events to be logged',
      },
      {
        id: 'AwsSolutions-SF2',
        reason: 'We do not need X-Ray tracing',
      },
    ],
    true
  );

  /* Return as a state machine object property */
  return {
    ...props,
    stateMachineObj: stateMachine,
  };
}

export function buildAllStepFunctions(scope: Construct, props: SfnsProps): SfnObject[] {
  // Initialize the step function objects
  const sfnObjects = [] as SfnObject[];

  // Iterate over lambdaLayerToMapping and create the lambda functions
  for (const sfnName of stepFunctionsNameList) {
    sfnObjects.push(
      buildStepFunction(scope, {
        stateMachineName: sfnName,
        ...props,
      })
    );
  }

  return sfnObjects;
}
