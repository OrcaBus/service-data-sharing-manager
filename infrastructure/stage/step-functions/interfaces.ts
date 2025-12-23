import { LambdaName, LambdaObject } from '../lambdas/interfaces';
import { IStateMachine, StateMachine } from 'aws-cdk-lib/aws-stepfunctions';
import { ITableV2 } from 'aws-cdk-lib/aws-dynamodb';
import { IBucket } from 'aws-cdk-lib/aws-s3';
import { EcsFargateTaskConstruct } from '@orcabus/platform-cdk-constructs/ecs';
import { IEventBus } from 'aws-cdk-lib/aws-events';
import { SsmParameterPaths } from '../ssm/interfaces';

export type StepFunctionsName =
  | 'packaging'
  | 'presigning'
  | 'pushIcav2Data'
  | 'pushS3Data'
  | 'updateFastqIngestIds'
  | 'push'
  | 'autoController'
  | 'autoPackage'
  | 'autoPush';

export const stepFunctionsNameList: StepFunctionsName[] = [
  'packaging',
  'presigning',
  'pushIcav2Data',
  'pushS3Data',
  'updateFastqIngestIds',
  'push',
  'autoController',
  'autoPackage',
  'autoPush',
];

export const lambdasInStepFunctions: Record<StepFunctionsName, LambdaName[]> = {
  packaging: [
    'handleWorkflowInputs',
    'updatePackagingJobApi',
    'getLibraryObjectFromLibraryOrcabusId',
    'getFastqsFromLibraryIdAndInstrumentRunIdList',
    'getFastqObjectFromFastqId',
    'getFileAndRelativePathFromS3AttributeId',
    'listPortalRunIdsInLibrary',
    'getWorkflowFromPortalRunId',
    'getFilesListFromPortalRunId',
    'getFilesAndRelativePathsFromS3AttributeIds',
    'updatePackagingJobApi',
  ],
  presigning: [
    'getDynamodbEvaluatedKeyList',
    'generatePresignedUrlsForDataObjects',
    'createScriptFromPresignedUrlsList',
  ],
  pushIcav2Data: ['queryAndCollectIcav2Prefixes'],
  pushS3Data: [
    'getS3DestinationAndSourceUriMappings',
    'createCsvForS3StepsCopy',
    'updatePushJobApi',
    'packageFileToJsonlData',
  ],
  updateFastqIngestIds: ['updateIngestId', 'getFastqsInPackagingJob'],
  push: ['updatePushJobApi', 'uploadPushJobToS3'],
  autoController: ['checkProjectInInstrumentRun'],
  autoPackage: ['triggerPackaging', 'checkPackagePushStatus', 'notifySlack'],
  autoPush: ['triggerPush', 'checkPackagePushStatus', 'notifySlack', 'extractSlackActionContext'],
};

export interface StepFunctionRequirements {
  needsEventPutPermissions?: boolean;
  needsEcsPermissions?: boolean;
  needsDbRwPermissions?: boolean;
  needsDbQueryPermissions?: boolean;
  needsNestedSfnPermissions?: boolean;
  needsDistributedMapPermissions?: boolean;
  isExpressSfn?: boolean;
  needsJobsConfigReadPermissions?: boolean;
  needsSsmPermissions?: boolean;
}

export const stepFunctionsRequirementsMap: Record<StepFunctionsName, StepFunctionRequirements> = {
  packaging: {
    needsEventPutPermissions: true,
    needsEcsPermissions: true,
    needsDbRwPermissions: true,
    needsDbQueryPermissions: true,
    needsDistributedMapPermissions: true,
  },
  presigning: {
    needsDbRwPermissions: true,
    needsDbQueryPermissions: true,
    isExpressSfn: true,
  },
  pushIcav2Data: {
    needsEventPutPermissions: true,
    needsDistributedMapPermissions: true,
  },
  pushS3Data: {
    needsNestedSfnPermissions: true,
    needsDistributedMapPermissions: true,
  },
  updateFastqIngestIds: {
    needsDistributedMapPermissions: true,
    needsSsmPermissions: true,
  },
  push: {
    needsNestedSfnPermissions: true,
  },
  autoController: {
    needsNestedSfnPermissions: true,
    needsEventPutPermissions: true,
    needsDistributedMapPermissions: true,
    needsJobsConfigReadPermissions: true,
  },
  autoPackage: {
    needsEventPutPermissions: true,
  },
  autoPush: {
    needsEventPutPermissions: true,
  },
};

export interface SfnProps {
  // Name of the state machine
  stateMachineName: StepFunctionsName;
  // List of lambda functions that are used in the state machine
  lambdaObjects: LambdaObject[];
  // Packaging lookup table
  packagingLookupTable: ITableV2;
  // S3 Steps Copy Bucket
  s3StepsCopyBucket: IBucket;
  s3StepsCopySfn: IStateMachine;
  s3StepsCopyPrefix: string;
  s3StepsCopyMidfix: string;
  s3StepsUseJsonLCopyFormat: boolean;
  // Packaging Bucket
  packagingBucket: IBucket;
  // ECS Cluster
  dataReportingEcsObject: EcsFargateTaskConstruct;
  // EventBus
  eventBusObject: IEventBus;
  // Data sharing S3 bucket
  dataSharingBucketName: string;
  // SSM Stuff
  ssmParameterPaths: SsmParameterPaths;
}

export interface SfnPropsWithStateMachine extends SfnProps {
  stateMachineObj: StateMachine;
}

export interface SfnObject {
  stateMachineName: StepFunctionsName;
  stateMachineObj: StateMachine;
}

export type SfnsProps = Omit<SfnProps, 'stateMachineName'>;
