/*
Build the ecs fargate task
*/

import { Construct } from 'constructs';
import {
  CPU_ARCHITECTURE_MAP,
  EcsFargateTaskConstruct,
  FargateEcsTaskConstructProps,
} from '@orcabus/platform-cdk-constructs/ecs';
import * as path from 'path';
import { CONTENT_INDEX_NAME, ECS_DIR } from '../constants';
import { BuildRMarkdownFargateEcsProps } from './interfaces';
import { NagSuppressions } from 'cdk-nag';
import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';

function buildEcsFargateTask(scope: Construct, id: string, props: FargateEcsTaskConstructProps) {
  /*
    Generate an ECS Fargate task construct with the provided properties.
    */
  return new EcsFargateTaskConstruct(scope, id, props);
}

export function buildRMarkdownFargateTask(
  scope: Construct,
  props: BuildRMarkdownFargateEcsProps
): EcsFargateTaskConstruct {
  /*
    Build the DataSharing RMarkdown Reporting Fargate task.

    We use 4 CPUs for this task
    and the docker path can be found under ECS_DIR / 'tasks', 'generate_data_summary_report'
    */

  const ecsTask = buildEcsFargateTask(scope, 'GenerateDataSummaryReport', {
    containerName: 'generate-data-summary-report',
    dockerPath: path.join(ECS_DIR, 'tasks', 'generate_data_summary_report'),
    nCpus: 8, // 8 CPUs
    memoryLimitGiB: 16, // 16 GB of memory (minimum for 8 CPUs)
    architecture: 'ARM64',
    runtimePlatform: CPU_ARCHITECTURE_MAP['ARM64'],
  });

  // Give the ecsTask access to the S3 bucket
  // Must be able to write to the packaging prefix
  // Since the output markdown files will be stored there
  props.packagingLookUpBucket.grantReadWrite(
    ecsTask.taskDefinition.taskRole,
    `${props.packagingLookUpPrefix}*`
  );

  // Needs access to the database
  props.packagingLookUpTable.grantReadData(ecsTask.taskDefinition.taskRole);

  // Needs query access to the dynamodb table
  // Give permissions to the container to access the table index
  // Grant query permissions on indexes
  ecsTask.taskDefinition.addToTaskRolePolicy(
    new iam.PolicyStatement({
      actions: ['dynamodb:Query'],
      resources: [
        `arn:aws:dynamodb:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:table/${props.packagingLookUpTable.tableName}/index/${CONTENT_INDEX_NAME}-index`,
      ],
    })
  );

  ecsTask.containerDefinition.addEnvironment(
    'DYNAMODB_TABLE_NAME',
    props.packagingLookUpTable.tableName
  );
  ecsTask.containerDefinition.addEnvironment('DYNAMODB_INDEX_NAME', CONTENT_INDEX_NAME);

  // Add suppressions for the task role
  // Since the task role needs to access the S3 bucket prefix
  NagSuppressions.addResourceSuppressions(
    [ecsTask.taskDefinition, ecsTask.taskExecutionRole],
    [
      {
        id: 'AwsSolutions-IAM5',
        reason: 'The task role needs to access the S3 bucket.',
      },
      {
        id: 'AwsSolutions-IAM4',
        reason:
          'We use the standard ecs task role for this task, which allows the guard duty agent to run alongside the task.',
      },
      {
        id: 'AwsSolutions-ECS2',
        reason:
          'The task is designed to run with some constant environment variables, not sure why this is a bad thing?',
      },
    ],
    true
  );

  return ecsTask;
}
