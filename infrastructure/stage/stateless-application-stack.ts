import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { StatelessApplicationStackConfig } from './interfaces';
import * as events from 'aws-cdk-lib/aws-events';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import { buildAllLambdas, buildDataSharingToolsLayer } from './lambdas';
import { DATA_SHARING_BUCKET_PREFIX, S3_STEPS_COPY_PREFIX } from './constants';
import { buildRMarkdownFargateTask } from './ecs';
import { buildAllStepFunctions } from './step-functions';
import {
  addHttpRoutes,
  buildApiGateway,
  buildApiIntegration,
  buildApiInterfaceLambda,
} from './api';
import { HOSTED_ZONE_DOMAIN_PARAMETER_NAME } from '@orcabus/platform-cdk-constructs/api-gateway';
import { StageName } from '@orcabus/platform-cdk-constructs/shared-config/accounts';

export type StatelessApplicationStackProps = cdk.StackProps & StatelessApplicationStackConfig;

export class StatelessApplicationStack extends cdk.Stack {
  public readonly stageName: StageName;
  constructor(scope: Construct, id: string, props: StatelessApplicationStackProps) {
    super(scope, id, props);

    /**
     * Stateless application stack here we:
     *  * Build the lambda functions
     *  * Build the ECS cluster for building the RMarkdown report
     *  * Build the AWS Step functions for orchestrating the workflows
     *  * Build the API Gateway for the stateless application
     */

    // Set the stage name
    this.stageName = props.stageName;

    /*
        Part 0: Import the necessary objects as constructs
         * eventBusName as an EventBus Object

         * packagingJobsTableName as DynamoDb Table Objects
         * pushJobsTableName as DynamoDb Table Objects
         * packagingLookUpTableName as DynamoDb Table Objects

         * dataSharingBucketName as S3 Bucket Object

         * s3StepsCopyBucketName as S3 Bucket Object
         * s3StepsCopySfnArn as Step Function Object
         */

    // Get the event bus from the props
    const eventBusObj = events.EventBus.fromEventBusName(
      this,
      props.eventBusName,
      props.eventBusName
    );

    // Get the DynamoDB tables from the props
    const packagingJobsTable = dynamodb.TableV2.fromTableName(
      this,
      'PackagingJobsTable',
      props.packagingJobsTableName
    );
    const pushJobsTable = dynamodb.TableV2.fromTableName(
      this,
      'PushJobsTable',
      props.pushJobsTableName
    );
    const packagingLookUpTable = dynamodb.TableV2.fromTableName(
      this,
      'PackagingLookUpTable',
      props.packagingLookUpTableName
    );

    // Get the S3 bucket from the props
    const dataSharingBucket = s3.Bucket.fromBucketName(
      this,
      'DataSharingBucket',
      props.dataSharingBucketName
    );

    // Get the S3 bucket for the Step Functions copy step
    const s3StepsCopyBucket = s3.Bucket.fromBucketName(
      this,
      'S3StepsCopyBucket',
      props.s3StepsCopyBucketName
    );

    // Get the Step Function for the S3 copy step
    const s3StepsCopySfn = sfn.StateMachine.fromStateMachineArn(
      this,
      'S3StepsCopySfn',
      props.s3StepsCopySfnArn
    );

    // Also build the datasharing tools layer
    const dataSharingToolsLayer = buildDataSharingToolsLayer(this);

    // Hosted Zone SSM Parameter Object
    // Get hosted zone name istring parameter
    const hostedZoneNameSsmParameter = ssm.StringParameter.fromStringParameterName(
      this,
      'hostedZoneName',
      HOSTED_ZONE_DOMAIN_PARAMETER_NAME
    );

    /*
        Part 1: Build the Lambda functions
         */
    const lambdas = buildAllLambdas(this, {
      dataSharingToolsLayer: dataSharingToolsLayer,
      packagingLookUpTable: packagingLookUpTable,
      s3StepsCopyBucket: s3StepsCopyBucket,
      s3StepsCopyBucketPrefix: S3_STEPS_COPY_PREFIX,
    });

    /*
        Part 2: Build the ECS cluster for building the RMarkdown report
        */
    const dataRmarkdownEcsCluster = buildRMarkdownFargateTask(this, {
      packagingLookUpBucket: dataSharingBucket,
      packagingLookUpPrefix: DATA_SHARING_BUCKET_PREFIX,
      packagingLookUpTable: packagingLookUpTable,
    });

    /*
        Part 3: Build the AWS Step Functions
        */
    const stepFunctions = buildAllStepFunctions(this, {
      // List of lambda functions that are used in the state machine
      lambdaObjects: lambdas,
      // Packaging lookup table
      packagingLookupTable: packagingLookUpTable,
      // S3 Steps Copy Bucket
      s3StepsCopyBucket: dataSharingBucket,
      s3StepsCopySfn: s3StepsCopySfn,
      // Packaging Bucket
      packagingBucket: dataSharingBucket,
      // ECS Cluster
      dataReportingEcsObject: dataRmarkdownEcsCluster,
      // EventBus
      eventBusObject: eventBusObj,
    });

    /*
        Part 4: API Gateway for the stateless application
        */
    // Build the API Gateway
    const lambdaApi = buildApiInterfaceLambda(this, {
      dataSharingLayer: dataSharingToolsLayer,
      sfnObjects: stepFunctions,
      packagingLookUpBucket: dataSharingBucket,
      hostedZoneSsmParameter: hostedZoneNameSsmParameter,
      eventBus: eventBusObj,
      packagingDynamoDbApiTable: packagingJobsTable,
      pushJobDynamoDbApiTable: pushJobsTable,
    });
    const apiGateway = buildApiGateway(this, props.apiGatewayCognitoProps);
    const apiIntegration = buildApiIntegration({
      lambdaFunction: lambdaApi,
    });
    addHttpRoutes(this, {
      apiGateway: apiGateway,
      apiIntegration: apiIntegration,
    });
  }
}
