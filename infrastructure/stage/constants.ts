// Application constants
import * as path from 'path';
import {
  ACCOUNT_ID_ALIAS,
  REGION,
  StageName,
} from '@orcabus/platform-cdk-constructs/shared-config/accounts';

// Directory constants
export const APP_ROOT = path.join(__dirname, '../../app');
export const LAMBDA_DIR = path.join(APP_ROOT, 'lambdas');
export const LAYERS_DIR = path.join(APP_ROOT, 'layers');
export const ECS_DIR = path.join(APP_ROOT, 'ecs');
export const STEP_FUNCTIONS_DIR = path.join(APP_ROOT, 'step-functions-templates');
export const INTERFACE_DIR = path.join(APP_ROOT, 'interface');

// Dynamodb
export const DYNAMODB_PACKAGING_API_TABLE_NAME = 'DataSharingPackagingApiTable';
export const DYNAMODB_PUSH_API_TABLE_NAME = 'DataSharingPushApiTable';
export const DYNAMODB_PACKAGING_LOOKUP_TABLE_NAME = 'DataSharingPackagingLookupTable';

// Indexes - Packaging Job API
export const PACKAGING_JOB_API_GLOBAL_SECONDARY_INDEX_NAMES = ['package_name', 'status'];
export const PACKAGING_JOB_API_GLOBAL_SECONDARY_INDEX_NON_KEY_ATTRIBUTE_NAMES = [
  'request_time',
  'completion_time',
];
// Indexes - Push Job API
export const PUSH_JOB_API_GLOBAL_SECONDARY_INDEX_NAMES = [
  'package_id', // Each push job is associated with a packaging job
  'package_name', // Not a typo, this is the same as packaging job API
  'status',
];
export const PUSH_JOB_API_GLOBAL_SECONDARY_INDEX_NON_KEY_ATTRIBUTE_NAMES = [
  'start_time',
  'end_time',
];
// Indexes - Packaging Lookup Table
export const CONTEXT_INDEX_NAME = 'context';
export const CONTENT_INDEX_NAME = 'content';
export const INDEX_PARTITION_KEY = 'context';
export const PACKAGING_LOOKUP_SECONDARY_INDEX_NAMES = [CONTEXT_INDEX_NAME, CONTENT_INDEX_NAME];
export const PACKAGING_LOOKUP_TABLE_GLOBAL_SECONDARY_INDEX_NAMES_BY_INDEX: Record<
  string,
  string[]
> = {
  [CONTEXT_INDEX_NAME]: ['job_id'],
  [CONTENT_INDEX_NAME]: ['job_id', 'content', 'presigned_url', 'presigned_expiry'],
};

// Event stuff
export const EVENT_BUS_NAME = 'OrcaBusMain';
export const STACK_SOURCE = 'orcabus.datasharing';
export const PACKAGING_JOB_STATE_CHANGE_EVENT_DETAIL_TYPE = 'DataPackagingJobStateChange';
export const PUSH_JOB_STATE_CHANGE_EVENT_DETAIL_TYPE = 'DataPushJobStateChange';
export const FASTQ_SYNC_DETAIL_TYPE = 'FastqSync';

// API
export const API_VERSION = 'v1';
export const API_NAME = 'DataSharingAPI';
export const API_SUBDOMAIN_NAME = 'data-sharing';

// Step functions
export const SFN_PREFIX = 'data-sharing';

// S3 Stuff
export const DATA_SHARING_BUCKET_NAME = 'data-sharing-artifacts-__ACCOUNT_ID__-__REGION__';
export const DATA_SHARING_BUCKET_PREFIX = 'packages';

// External S3 Steps Copy Service
/*
S3 Copy Steps Function ARNs by account id
*/
export const s3CopyStepsBucket: Record<StageName, string> = {
  BETA: 'stepss3copy-working66f7dd3f-x4jwbnt6qvxc', // pragma: allowlist secret
  GAMMA: 'stg-stepss3copystack-stepss3copyworking01b34927-szqxpff5lsbx', // pragma: allowlist secret
  PROD: 'prod-stepss3copystack-stepss3copyworking01b34927-mp9y88d9e1py', // pragma: allowlist secret
};

export const S3_STEPS_COPY_PREFIX: Record<StageName, string> = {
  BETA: 'a-working-folder/',
  GAMMA: '',
  PROD: '',
};

export const S3_STEPS_COPY_MIDFIX: string = 'DATA_SHARING/';

export const s3CopyStepsFunctionArn: Record<StageName, string> = {
  BETA: `arn:aws:states:${REGION}:${ACCOUNT_ID_ALIAS['BETA']}:stateMachine:StepsS3CopyStateMachine157A1409-jx4WNxpdckgQ`, // pragma: allowlist secret
  GAMMA: `arn:aws:states:${REGION}:${ACCOUNT_ID_ALIAS['GAMMA']}:stateMachine:StepsS3CopyStateMachine157A1409-ikBos7HzwDtL`, // pragma: allowlist secret
  PROD: `arn:aws:states:${REGION}:${ACCOUNT_ID_ALIAS['PROD']}:stateMachine:StepsS3CopyStateMachine157A1409-YbCgUX7dCZRm`, // pragma: allowlist secret
};

// S3 Steps Copy Implementations
export const USE_JSONL_COPY_FORMAT: Record<StageName, boolean> = {
  BETA: true,
  GAMMA: false,
  PROD: false,
};
