/**
 * Use the PythonUvFunction script to build the lambda functions
 */
import {
  lambdaNameList,
  LambdaProps,
  lambdaRequirementsMap,
  LambdaObject,
  BuildAllLambdaProps,
} from './interfaces';
import { getPythonUvDockerImage, PythonUvFunction } from '@orcabus/platform-cdk-constructs/lambda';
import { Construct } from 'constructs';
import { camelCaseToSnakeCase } from '../utils';
import * as path from 'path';
import { Duration } from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import {
  CONTENT_INDEX_NAME,
  CONTEXT_INDEX_NAME,
  LAMBDA_DIR,
  LAYERS_DIR,
  MART_BUCKET_PREFIX,
  MART_ENV_VARS,
  PACKAGING_LOOKUP_SECONDARY_INDEX_NAMES,
  SLACK_BOT_TOKEN_SECRET_NAME,
  SLACK_CONFIG_SECRET_NAME,
} from '../constants';
import { NagSuppressions } from 'cdk-nag';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as cdk from 'aws-cdk-lib';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { PythonLayerVersion } from '@aws-cdk/aws-lambda-python-alpha';

function buildLambdaFunction(scope: Construct, props: LambdaProps): LambdaObject {
  const lambdaNameToSnakeCase = camelCaseToSnakeCase(props.lambdaName);
  const lambdaRequirements = lambdaRequirementsMap[props.lambdaName];
  const lambdaObject = new PythonUvFunction(scope, props.lambdaName, {
    entry: path.join(LAMBDA_DIR, lambdaNameToSnakeCase + '_py'),
    runtime: lambda.Runtime.PYTHON_3_12,
    architecture: lambda.Architecture.ARM_64,
    index: lambdaNameToSnakeCase + '.py',
    handler: 'handler',
    timeout: Duration.seconds(300),
    includeOrcabusApiToolsLayer: lambdaRequirements.needsOrcabusApiToolsLayer,
    includeMartLayer: lambdaRequirements.needsMartLayer,
  });

  if (lambdaRequirements.needsDataSharingToolsLayer) {
    lambdaObject.addLayers(props.dataSharingToolsLayer);
  }

  if (lambdaRequirements.needsDbPermissions) {
    props.packagingLookUpTable.grantReadData(lambdaObject);
    // Grant query permissions on indexes
    const packaging_index_arn_list: string[] = PACKAGING_LOOKUP_SECONDARY_INDEX_NAMES.map(
      (index_name) => {
        return `arn:aws:dynamodb:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:table/${props.packagingLookUpTable.tableName}/index/${index_name}-index`;
      }
    );

    lambdaObject.currentVersion.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['dynamodb:Query'],
        resources: [...packaging_index_arn_list],
      })
    );

    // Add the environment variable 'PACKAGING_TABLE_NAME' to the lambda function
    lambdaObject.addEnvironment('PACKAGING_TABLE_NAME', props.packagingLookUpTable.tableName);
    lambdaObject.addEnvironment('CONTENT_INDEX_NAME', CONTENT_INDEX_NAME);
    lambdaObject.addEnvironment('CONTEXT_INDEX_NAME', CONTEXT_INDEX_NAME);
  }

  if (lambdaRequirements.needsMartLayer) {
    /* Add env vars and nag suppressions for mart access */
    // Iterate over the MART_ENV_VARS key, value pairs and add them as environment variables to the lambda function
    Object.entries(MART_ENV_VARS).forEach(([key, value]) => {
      lambdaObject.addEnvironment(key, value);
    });

    // Add in the bucket permissions
    props.athenaQueryResultsBucket.grantReadWrite(
      lambdaObject.currentVersion,
      path.join(MART_BUCKET_PREFIX, '*')
    );

    // Add nag suppressions
    NagSuppressions.addResourceSuppressions(
      lambdaObject,
      [
        {
          id: 'AwsSolutions-IAM5',
          reason: 'Mart need asterisk across athena resources',
        },
      ],
      true
    );
  }

  if (lambdaRequirements.needsPackagingBucketPermissions) {
    // Grant read/write permissions to the packaging bucket
    props.packagingLookUpBucket.grantReadWrite(lambdaObject.currentVersion);
    NagSuppressions.addResourceSuppressions(
      lambdaObject,
      [
        {
          id: 'AwsSolutions-IAM5',
          reason: 'Packaging bucket needs asterisk across s3 resources',
        },
      ],
      true
    );
  }

  if (lambdaRequirements.needsStepsS3UploadPermissions) {
    props.s3StepsCopyBucket.grantReadWrite(
      lambdaObject.currentVersion,
      path.join(props.s3StepsCopyBucketPrefix, '*')
    );
    NagSuppressions.addResourceSuppressions(
      lambdaObject,
      [
        {
          id: 'AwsSolutions-IAM5',
          reason: 'Lambda needs asterisk across s3 resources',
        },
      ],
      true
    );
  }

  // Allow the notifier Lambda to read the Slack bot token and config secrets at runtime
  if (props.lambdaName === 'notifySlack') {
    const slackBotToken = secretsmanager.Secret.fromSecretNameV2(
      scope,
      'SlackBotTokenSecret',
      SLACK_BOT_TOKEN_SECRET_NAME
    );
    slackBotToken.grantRead(lambdaObject);

    const slackConfig = secretsmanager.Secret.fromSecretNameV2(
      scope,
      'AutoDataSharingSlackConfigForNotify',
      SLACK_CONFIG_SECRET_NAME
    );
    slackConfig.grantRead(lambdaObject);
  }

  // Allow the checkSlackPush Lambda to read the allowed-users secret at runtime
  if (props.lambdaName === 'checkSlackPush') {
    const slackAllowedUsers = secretsmanager.Secret.fromSecretNameV2(
      scope,
      'AutoDataSharingSlackConfigForCheckPush',
      SLACK_CONFIG_SECRET_NAME
    );
    slackAllowedUsers.grantRead(lambdaObject);
  }

  return {
    lambdaName: props.lambdaName,
    lambdaFunction: lambdaObject,
  };
}

export function buildAllLambdas(scope: Construct, props: BuildAllLambdaProps): LambdaObject[] {
  const lambdaList: LambdaObject[] = [];
  for (const lambdaName of lambdaNameList) {
    lambdaList.push(
      buildLambdaFunction(scope, {
        lambdaName: lambdaName,
        ...props,
      })
    );
  }

  // Add cdk nag stack suppressions
  NagSuppressions.addResourceSuppressions(
    lambdaList.map((lambdaObject) => lambdaObject.lambdaFunction),
    [
      {
        id: 'AwsSolutions-IAM4',
        reason: 'We use the AWS Lambda basic execution role to run the lambdas.',
      },
      {
        id: 'AwsSolutions-L1',
        reason: 'Were currently using Python 3.12',
      },
    ],
    true
  );

  return lambdaList;
}

export function buildDataSharingToolsLayer(scope: Construct): PythonLayerVersion {
  /**
        Build the bssh tools layer, used by the get manifest lambda function
        // Use getPythonUvDockerImage once we export this as a function from the
        // platform-cdk-constructs repo
    */
  return new PythonLayerVersion(scope, 'data-sharing-tools-layer', {
    entry: path.join(LAYERS_DIR, 'data_sharing_tools_layer'),
    compatibleRuntimes: [lambda.Runtime.PYTHON_3_12],
    compatibleArchitectures: [lambda.Architecture.ARM_64],
    bundling: {
      image: getPythonUvDockerImage(),
      commandHooks: {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        beforeBundling(inputDir: string, outputDir: string): string[] {
          return [];
        },
        afterBundling(inputDir: string, outputDir: string): string[] {
          return [
            `pip install ${inputDir} --target ${outputDir}`,
            `find ${outputDir} -name 'pandas' -exec rm -rf {}/tests/ \\;`,
          ];
        },
      },
    },
  });
}
