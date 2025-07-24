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
  | 'queryAndCollectIcav2Prefixes'
  | 'updatePackagingJobApi'
  | 'updatePushJobApi'
  | 'uploadArchiveFileListAsCsv'
  | 'uploadPushJobToS3';

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
  'queryAndCollectIcav2Prefixes',
  'updatePackagingJobApi',
  'updatePushJobApi',
  'uploadArchiveFileListAsCsv',
  'uploadPushJobToS3',
];

export interface Requirements {
  needsOrcabusApiToolsLayer?: boolean;
  needsDataSharingToolsLayer?: boolean;
  needsMartLayer?: boolean;
  needsDbPermissions?: boolean;
  needsStsPermissions?: boolean;
  needsStepsS3UploadPermissions?: boolean;
  needsPackagingBucketPermissions?: boolean;
}

export const lambdaRequirementsMap: { [key in LambdaName]: Requirements } = {
  createCsvForS3StepsCopy: {
    needsStsPermissions: true,
    needsStepsS3UploadPermissions: true,
  },
  createScriptFromPresignedUrlsList: {
    needsDataSharingToolsLayer: true,
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
  },
  listPortalRunIdsInLibrary: {
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
