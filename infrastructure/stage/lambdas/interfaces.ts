import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { ILayerVersion } from 'aws-cdk-lib/aws-lambda';
import { ITableV2 } from 'aws-cdk-lib/aws-dynamodb';
import { IBucket } from 'aws-cdk-lib/aws-s3';

export type LambdaName =
  | 'createCsvForS3StepsCopy'
  | 'createScriptFromPresignedUrlsList'
  | 'generatePresignedUrlsForDataObjects'
  | 'getFastqObjectFromFastqId'
  | 'getFileAndRelativePathFromS3AttributeId'
  | 'getFilesAndRelativePathsFromS3AttributeIds'
  | 'getLibraryObjectFromLibraryOrcabusId'
  | 'getS3DestinationAndSourceUriMappings'
  | 'getWorkflowFromPortalRunId'
  | 'handleWorkflowInputs'
  | 'getFastqsFromLibraryIdAndInstrumentRunIdList'
  | 'getFilesListFromPortalRunId'
  | 'listPortalRunIdsInLibrary'
  | 'packageFileToJsonlData'
  | 'queryAndCollectIcav2Prefixes'
  | 'updatePackagingJobApi'
  | 'updatePushJobApi'
  | 'uploadArchiveFileListAsCsv'
  | 'uploadPushJobToS3'
  | 'getDynamodbEvaluatedKeyList'
  | 'triggerPackaging'
  | 'checkPackagePushStatus'
  | 'triggerPush'
  | 'checkProjectInInstrumentRun'
  | 'notifySlack';

export const lambdaNameList: LambdaName[] = [
  'createCsvForS3StepsCopy',
  'createScriptFromPresignedUrlsList',
  'generatePresignedUrlsForDataObjects',
  'getFastqObjectFromFastqId',
  'getFileAndRelativePathFromS3AttributeId',
  'getFilesAndRelativePathsFromS3AttributeIds',
  'getLibraryObjectFromLibraryOrcabusId',
  'getS3DestinationAndSourceUriMappings',
  'getWorkflowFromPortalRunId',
  'handleWorkflowInputs',
  'getFastqsFromLibraryIdAndInstrumentRunIdList',
  'getFilesListFromPortalRunId',
  'listPortalRunIdsInLibrary',
  'packageFileToJsonlData',
  'queryAndCollectIcav2Prefixes',
  'updatePackagingJobApi',
  'updatePushJobApi',
  'uploadArchiveFileListAsCsv',
  'uploadPushJobToS3',
  'getDynamodbEvaluatedKeyList',
  'triggerPackaging',
  'checkPackagePushStatus',
  'triggerPush',
  'checkProjectInInstrumentRun',
  'notifySlack',
];

export interface Requirements {
  needsOrcabusApiToolsLayer?: boolean;
  needsDataSharingToolsLayer?: boolean;
  needsMartLayer?: boolean;
  needsDbPermissions?: boolean;
  needsStepsS3UploadPermissions?: boolean;
  needsPackagingBucketPermissions?: boolean;
  needsAutoJobsSsmAccess?: boolean;
}

export const lambdaRequirementsMap: { [key in LambdaName]: Requirements } = {
  createCsvForS3StepsCopy: {
    needsStepsS3UploadPermissions: true,
  },
  createScriptFromPresignedUrlsList: {
    needsDataSharingToolsLayer: true,
    needsOrcabusApiToolsLayer: true,
    needsDbPermissions: true,
    needsPackagingBucketPermissions: true,
  },
  generatePresignedUrlsForDataObjects: {
    needsOrcabusApiToolsLayer: true,
  },
  getFastqObjectFromFastqId: {
    needsOrcabusApiToolsLayer: true,
  },
  getFileAndRelativePathFromS3AttributeId: {
    needsOrcabusApiToolsLayer: true,
    needsDataSharingToolsLayer: true,
  },
  getFilesAndRelativePathsFromS3AttributeIds: {
    needsDataSharingToolsLayer: true,
    needsOrcabusApiToolsLayer: true,
  },
  getLibraryObjectFromLibraryOrcabusId: {
    needsOrcabusApiToolsLayer: true,
  },
  getS3DestinationAndSourceUriMappings: {
    needsDataSharingToolsLayer: true,
    needsOrcabusApiToolsLayer: true,
    needsDbPermissions: true,
  },
  getWorkflowFromPortalRunId: {
    needsOrcabusApiToolsLayer: true,
    needsMartLayer: true,
  },
  handleWorkflowInputs: {
    needsOrcabusApiToolsLayer: true,
  },
  getFastqsFromLibraryIdAndInstrumentRunIdList: {
    needsOrcabusApiToolsLayer: true,
  },
  getFilesListFromPortalRunId: {
    needsOrcabusApiToolsLayer: true,
  },
  queryAndCollectIcav2Prefixes: {
    needsOrcabusApiToolsLayer: true,
    needsDataSharingToolsLayer: true,
    needsDbPermissions: true,
  },
  listPortalRunIdsInLibrary: {
    needsOrcabusApiToolsLayer: true,
  },
  packageFileToJsonlData: {
    needsDbPermissions: true,
    needsStepsS3UploadPermissions: true,
    needsDataSharingToolsLayer: true,
    needsOrcabusApiToolsLayer: true,
  },
  updatePackagingJobApi: {
    needsOrcabusApiToolsLayer: true,
  },
  updatePushJobApi: {
    needsOrcabusApiToolsLayer: true,
  },
  uploadArchiveFileListAsCsv: {
    needsDataSharingToolsLayer: true,
    needsOrcabusApiToolsLayer: true,
  },
  uploadPushJobToS3: {
    needsDbPermissions: true,
    needsDataSharingToolsLayer: true,
    needsPackagingBucketPermissions: true,
    needsOrcabusApiToolsLayer: true,
  },
  getDynamodbEvaluatedKeyList: {
    needsDbPermissions: true,
  },
  triggerPackaging: {
    needsOrcabusApiToolsLayer: true,
  },
  checkPackagePushStatus: {
    needsOrcabusApiToolsLayer: true,
  },
  triggerPush: {
    needsOrcabusApiToolsLayer: true,
  },
  checkProjectInInstrumentRun: {
    needsOrcabusApiToolsLayer: true,
  },
  notifySlack: {},
};

export interface LambdaProps {
  // Lambda name
  lambdaName: LambdaName;
  // Layer versions
  dataSharingToolsLayer: ILayerVersion;
  // Database permissions
  packagingLookUpTable: ITableV2;
  packagingLookUpBucket: IBucket;
  // S3 Steps Copy Permissions
  s3StepsCopyBucket: IBucket;
  s3StepsCopyBucketPrefix: string;
}

export type BuildAllLambdaProps = Omit<LambdaProps, 'lambdaName'>;

export interface LambdaObject {
  // Lambda name
  lambdaName: LambdaName;
  lambdaFunction: PythonFunction;
}
