import { PythonUvFunction } from '@orcabus/platform-cdk-constructs/lambda';
import path from 'path';
import {
  API_SUBDOMAIN_NAME,
  API_VERSION,
  DATA_SHARING_BUCKET_PREFIX,
  EVENT_BUS_NAME,
  INTERFACE_DIR,
  PACKAGING_JOB_API_GLOBAL_SECONDARY_INDEX_NAMES,
  PACKAGING_JOB_STATE_CHANGE_EVENT_DETAIL_TYPE,
  PUSH_JOB_API_GLOBAL_SECONDARY_INDEX_NAMES,
  PUSH_JOB_STATE_CHANGE_EVENT_DETAIL_TYPE,
  STACK_SOURCE,
} from '../constants';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Duration } from 'aws-cdk-lib';
import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import { NagSuppressions } from 'cdk-nag';
import {
  OrcaBusApiGateway,
  OrcaBusApiGatewayProps,
} from '@orcabus/platform-cdk-constructs/api-gateway';
import { HttpLambdaIntegration } from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import {
  HttpMethod,
  HttpNoneAuthorizer,
  HttpRoute,
  HttpRouteKey,
} from 'aws-cdk-lib/aws-apigatewayv2';
import { Construct } from 'constructs';
import {
  BuildApiIntegrationProps,
  BuildHttpRoutesProps,
  LambdaApiFunctionProps,
  BuildSlackAutoPushApiProps,
} from './interfaces';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as logs from 'aws-cdk-lib/aws-logs';

export function buildApiInterfaceLambda(scope: Construct, props: LambdaApiFunctionProps) {
  const lambdaApiFunction = new PythonUvFunction(scope, 'DataSharingApi', {
    entry: path.join(INTERFACE_DIR),
    runtime: lambda.Runtime.PYTHON_3_12,
    architecture: lambda.Architecture.ARM_64,
    index: 'handler.py',
    handler: 'handler',
    timeout: Duration.seconds(60),
    memorySize: 2048,
    includeOrcabusApiToolsLayer: true,
    includeFastApiLayer: true,
    environment: {
      /* DynamoDB env vars */
      DYNAMODB_HOST: `https://dynamodb.${cdk.Aws.REGION}.amazonaws.com`,
      DYNAMODB_PACKAGING_JOB_TABLE_NAME: props.packagingDynamoDbApiTable.tableName,
      DYNAMODB_PUSH_JOB_TABLE_NAME: props.pushJobDynamoDbApiTable.tableName,
      /* SSM and Secrets Manager env vars */
      DATA_SHARING_BASE_URL: `https://${API_SUBDOMAIN_NAME}.${props.hostedZoneSsmParameter.stringValue}`,
      /* Event bridge env vars */
      EVENT_BUS_NAME: EVENT_BUS_NAME,
      EVENT_SOURCE: STACK_SOURCE,
      /* Event detail types */
      EVENT_DETAIL_TYPE_PACKAGING_JOB_STATE_CHANGE: PACKAGING_JOB_STATE_CHANGE_EVENT_DETAIL_TYPE,
      EVENT_DETAIL_TYPE_PUSH_JOB_STATE_CHANGE: PUSH_JOB_STATE_CHANGE_EVENT_DETAIL_TYPE,
      /* Package bucket */
      PACKAGE_BUCKET_NAME: props.packagingLookUpBucket.bucketName,
    },
  });

  // Add the data sharing API tools layer
  lambdaApiFunction.addLayers(props.dataSharingLayer);

  // Give lambda function permissions to put events on the event bus
  props.eventBus.grantPutEventsTo(lambdaApiFunction.currentVersion);

  // Add in permissions and env vars to the three state machines
  for (const sfnObject of props.sfnObjects) {
    switch (sfnObject.stateMachineName) {
      // For packaging
      case 'packaging': {
        lambdaApiFunction.addEnvironment(
          'PACKAGE_JOB_STATE_MACHINE_ARN',
          sfnObject.stateMachineObj.stateMachineArn
        );
        sfnObject.stateMachineObj.grantStartExecution(lambdaApiFunction.currentVersion);
        break;
      }
      // For presigning
      case 'presigning': {
        lambdaApiFunction.addEnvironment(
          'PRESIGN_STATE_MACHINE_ARN',
          sfnObject.stateMachineObj.stateMachineArn
        );
        sfnObject.stateMachineObj.grantStartSyncExecution(lambdaApiFunction.currentVersion);
        break;
      }
      case 'push': {
        lambdaApiFunction.addEnvironment(
          'PUSH_JOB_STATE_MACHINE_ARN',
          sfnObject.stateMachineObj.stateMachineArn
        );
        sfnObject.stateMachineObj.grantStartExecution(lambdaApiFunction.currentVersion);
        break;
      }
    }
  }

  // Allow read/write access to the dynamodb table
  props.packagingDynamoDbApiTable.grantReadWriteData(lambdaApiFunction.currentVersion);
  props.pushJobDynamoDbApiTable.grantReadWriteData(lambdaApiFunction.currentVersion);

  // Lambda needs read access to the packaging bucket in order to generate the presigned urls
  props.packagingLookUpBucket.grantRead(
    lambdaApiFunction.currentVersion,
    path.join(DATA_SHARING_BUCKET_PREFIX, '*')
  );

  // Grant query permissions on indexes
  const packaging_index_arn_list: string[] = PACKAGING_JOB_API_GLOBAL_SECONDARY_INDEX_NAMES.map(
    (index_name) => {
      return `arn:aws:dynamodb:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:table/${props.packagingDynamoDbApiTable.tableName}/index/${index_name}-index`;
    }
  );
  const push_index_arn_list: string[] = PUSH_JOB_API_GLOBAL_SECONDARY_INDEX_NAMES.map(
    (index_name) => {
      return `arn:aws:dynamodb:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:table/${props.pushJobDynamoDbApiTable.tableName}/index/${index_name}-index`;
    }
  );

  lambdaApiFunction.currentVersion.addToRolePolicy(
    new iam.PolicyStatement({
      actions: ['dynamodb:Query'],
      resources: [...packaging_index_arn_list, ...push_index_arn_list],
    })
  );

  NagSuppressions.addResourceSuppressions(
    lambdaApiFunction,
    [
      {
        id: 'AwsSolutions-IAM5',
        reason: 'Need access to packaging look up bucket',
      },
      {
        id: 'AwsSolutions-IAM4',
        reason: 'We use the AWS Lambda Basic Execution Role',
      },
      {
        id: 'AwsSolutions-L1',
        reason: 'We are using Python 3.12, calm down please',
      },
    ],
    true
  );

  return lambdaApiFunction;
}

export function buildApiGateway(
  scope: Construct,
  props: OrcaBusApiGatewayProps
): OrcaBusApiGateway {
  return new OrcaBusApiGateway(scope, 'apiGateway', props);
}

export function buildApiIntegration(props: BuildApiIntegrationProps): HttpLambdaIntegration {
  return new HttpLambdaIntegration('ApiIntegration', props.lambdaFunction);
}

// Add the http routes to the API Gateway
export function addHttpRoutes(scope: Construct, props: BuildHttpRoutesProps) {
  // Routes for API schemas
  const schemaRoute = new HttpRoute(scope, 'GetSchemaHttpRoute', {
    httpApi: props.apiGateway.httpApi,
    integration: props.apiIntegration,
    authorizer: new HttpNoneAuthorizer(), // No auth needed for schema
    routeKey: HttpRouteKey.with(`/schema/{PROXY+}`, HttpMethod.GET),
  });
  NagSuppressions.addResourceSuppressions(
    schemaRoute,
    [
      {
        id: 'AwsSolutions-APIG4',
        reason: 'This is a public API endpoint for schema access, no auth needed.',
      },
    ],
    true
  );
  new HttpRoute(scope, 'GetHttpRoute', {
    httpApi: props.apiGateway.httpApi,
    integration: props.apiIntegration,
    routeKey: HttpRouteKey.with(`/api/${API_VERSION}/{PROXY+}`, HttpMethod.GET),
  });
  new HttpRoute(scope, 'PostHttpRoute', {
    httpApi: props.apiGateway.httpApi,
    integration: props.apiIntegration,
    authorizer: props.apiGateway.authStackHttpLambdaAuthorizer,
    routeKey: HttpRouteKey.with(`/api/${API_VERSION}/{PROXY+}`, HttpMethod.POST),
  });
  new HttpRoute(scope, 'PatchHttpRoute', {
    httpApi: props.apiGateway.httpApi,
    integration: props.apiIntegration,
    authorizer: props.apiGateway.authStackHttpLambdaAuthorizer,
    routeKey: HttpRouteKey.with(`/api/${API_VERSION}/{PROXY+}`, HttpMethod.PATCH),
  });
  new HttpRoute(scope, 'DeleteHttpRoute', {
    httpApi: props.apiGateway.httpApi,
    integration: props.apiIntegration,
    authorizer: props.apiGateway.authStackHttpLambdaAuthorizer,
    routeKey: HttpRouteKey.with(`/api/${API_VERSION}/{PROXY+}`, HttpMethod.DELETE),
  });
}

// Build Slack API Gateway for AutoPush feature
export function buildSlackAutoPushApi(scope: Construct, props: BuildSlackAutoPushApiProps) {
  // Create CloudWatch Log Group for API Gateway access logs
  const accessLogGroup = new logs.LogGroup(scope, 'AutoPushSlackApiAccessLogs', {
    retention: logs.RetentionDays.ONE_MONTH,
  });
  // Create the API Gateway
  const slackApi = new apigateway.RestApi(scope, 'AutoPushSlackApi', {
    restApiName: 'AutoPushSlackApi',
    description: 'Slack actions endpoint for Auto Push feature.',
    endpointConfiguration: {
      types: [apigateway.EndpointType.REGIONAL],
    },
    deployOptions: {
      accessLogDestination: new apigateway.LogGroupLogDestination(accessLogGroup),
      accessLogFormat: apigateway.AccessLogFormat.jsonWithStandardFields(),
      loggingLevel: apigateway.MethodLoggingLevel.INFO,
      dataTraceEnabled: false,
      metricsEnabled: true,
    },
  });

  // Create the /slack/actions resource
  const actions = slackApi.root.addResource('slack').addResource('actions');

  // Create request validator
  const requestValidator = new apigateway.RequestValidator(
    scope,
    'AutoPushSlackApiRequestValidator',
    {
      restApi: slackApi,
      validateRequestBody: true,
      validateRequestParameters: true,
    }
  );

  const slackApiAutoPushRole = new iam.Role(scope, 'SlackApiAutoPushRole', {
    assumedBy: new iam.ServicePrincipal('apigateway.amazonaws.com'),
    description: 'Role assumed by Slack REST API Gateway to start autoPush executions',
  });

  props.autoPushSfn.grantStartExecution(slackApiAutoPushRole);
  // TODO: proper, no hardoded requestTemplates
  const startExecutionIntegration = new apigateway.AwsIntegration({
    service: 'states',
    action: 'StartExecution',
    integrationHttpMethod: 'POST',
    options: {
      credentialsRole: slackApiAutoPushRole,
      passthroughBehavior: apigateway.PassthroughBehavior.WHEN_NO_MATCH,
      timeout: cdk.Duration.millis(29000),
      requestTemplates: {
        'application/x-www-form-urlencoded': `{
          "stateMachineArn": "${props.autoPushSfn.stateMachineArn}",
          "name": "$context.requestId",
          "input": "{\\"slackBody\\":\\"$util.escapeJavaScript($input.body)\\",\\"headers\\":\\"$util.escapeJavaScript($input.params().header)\\"}"
        }`,
      },
      integrationResponses: [
        {
          statusCode: '200',
          responseTemplates: { 'application/json': '' },
        },
      ],
    },
  });

  // Capture the method so we can add suppressions
  const postMethod = actions.addMethod('POST', startExecutionIntegration, {
    authorizationType: apigateway.AuthorizationType.NONE,
    requestValidator: requestValidator,
    requestParameters: {
      'method.request.header.X-Slack-Request-Timestamp': true,
      'method.request.header.X-Slack-Signature': true,
    },

    methodResponses: [{ statusCode: '200' }],
  });

  // Suppress APIG4 + COG4 on the method since we are not using auth here
  NagSuppressions.addResourceSuppressions(
    postMethod,
    [
      {
        id: 'AwsSolutions-APIG4',
        reason: 'Slack uses signing-secret verification, not API Gateway auth.',
      },
      {
        id: 'AwsSolutions-COG4',
        reason: 'Slack cannot use a Cognito authorizer.',
      },
    ],
    true
  );
  // Suppress IAM4 on the API Gateway since it uses a managed policy for CloudWatch logging
  NagSuppressions.addResourceSuppressions(
    slackApi,
    [
      {
        id: 'AwsSolutions-IAM4',
        reason:
          'API Gateway uses an AWS-managed policy (AmazonAPIGatewayPushToCloudWatchLogs) for its CloudWatchRole.',
      },
    ],
    true
  );

  return slackApi;
}
