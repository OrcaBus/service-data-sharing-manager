import { getDefaultApiGatewayConfiguration } from '@orcabus/platform-cdk-constructs/api-gateway';
import {
  API_NAME,
  API_SUBDOMAIN_NAME,
  DATA_SHARING_BUCKET_NAME,
  DYNAMODB_PACKAGING_API_TABLE_NAME,
  DYNAMODB_PACKAGING_LOOKUP_TABLE_NAME,
  DYNAMODB_PUSH_API_TABLE_NAME,
  EVENT_BUS_NAME,
  S3_STEPS_COPY_MIDFIX,
  S3_STEPS_COPY_PREFIX,
  s3CopyStepsBucket,
  s3CopyStepsFunctionArn,
  USE_JSONL_COPY_FORMAT,
} from './constants';
import {
  ACCOUNT_ID_ALIAS,
  REGION,
  StageName,
} from '@orcabus/platform-cdk-constructs/shared-config/accounts';
import { StatefulApplicationStackConfig, StatelessApplicationStackConfig } from './interfaces';

export const getStatefulApplicationStackProps = (
  stage: StageName
): StatefulApplicationStackConfig => {
  return {
    // Table names
    packagingJobsTableName: DYNAMODB_PACKAGING_API_TABLE_NAME,
    pushJobsTableName: DYNAMODB_PUSH_API_TABLE_NAME,
    packagingLookUpTableName: DYNAMODB_PACKAGING_LOOKUP_TABLE_NAME,

    // S3 Bucket names
    dataSharingBucketName: DATA_SHARING_BUCKET_NAME.replace(
      '__ACCOUNT_ID__',
      ACCOUNT_ID_ALIAS[stage]
    ).replace('__REGION__', REGION),
  };
};

export const getStatelessApplicationStackProps = (
  stage: StageName
): StatelessApplicationStackConfig => {
  return {
    // Stage name
    stageName: stage,
    // Event stuff
    eventBusName: EVENT_BUS_NAME,

    // Table names
    packagingJobsTableName: DYNAMODB_PACKAGING_API_TABLE_NAME,
    pushJobsTableName: DYNAMODB_PUSH_API_TABLE_NAME,
    packagingLookUpTableName: DYNAMODB_PACKAGING_LOOKUP_TABLE_NAME,

    // S3 stuff
    dataSharingBucketName: DATA_SHARING_BUCKET_NAME.replace(
      '__ACCOUNT_ID__',
      ACCOUNT_ID_ALIAS[stage]
    ).replace('__REGION__', REGION),

    // Steps Copy stuff
    s3StepsCopyBucketName: s3CopyStepsBucket[stage],
    s3StepsCopySfnArn: s3CopyStepsFunctionArn[stage],
    s3StepsCopyPrefix: S3_STEPS_COPY_PREFIX[stage],
    s3StepsCopyMidfix: S3_STEPS_COPY_MIDFIX,
    s3StepsUseJsonLCopyFormat: USE_JSONL_COPY_FORMAT[stage],

    /* API Stuff */
    apiGatewayCognitoProps: {
      ...getDefaultApiGatewayConfiguration(stage),
      apiName: API_NAME,
      customDomainNamePrefix: API_SUBDOMAIN_NAME,
    },
  };
};
