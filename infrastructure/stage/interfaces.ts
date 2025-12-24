/*
The configuration properties for the application stacks (stateless and stateful)
 */

import { OrcaBusApiGatewayProps } from '@orcabus/platform-cdk-constructs/api-gateway';
import { StageName } from '@orcabus/platform-cdk-constructs/shared-config/accounts';
import { SsmParameterPaths, SsmParameterProps } from './ssm/interfaces';

export interface StatefulApplicationStackConfig {
  // Table names
  packagingJobsTableName: string;
  pushJobsTableName: string;
  packagingLookUpTableName: string;

  // S3 Bucket names
  dataSharingBucketName: string;

  // SSM Stuff
  ssmParameters: SsmParameterProps;
}

export interface StatelessApplicationStackConfig {
  // Stage name
  stageName: StageName;

  // Event stuff
  eventBusName: string;

  // Table names
  packagingJobsTableName: string;
  pushJobsTableName: string;
  packagingLookUpTableName: string;

  // S3 stuff
  dataSharingBucketName: string;

  // Athena stuff
  athenaQueryResultsBucketName: string;

  // Steps Copy stuff
  s3StepsCopyBucketName: string;
  s3StepsCopySfnArn: string;
  s3StepsCopyPrefix: string;
  s3StepsCopyMidfix: string;
  s3StepsUseJsonLCopyFormat: boolean;

  /* API Stuff */
  apiGatewayCognitoProps: OrcaBusApiGatewayProps;

  /* SSM Stuff */
  ssmParameterPaths: SsmParameterPaths;

  /* Auto Data Sharing Stuff */
  autoPushSfnArn: string;
}
