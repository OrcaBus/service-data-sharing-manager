import { RemovalPolicy } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import {
  AttributeType,
  GlobalSecondaryIndexPropsV2,
  ProjectionType,
} from 'aws-cdk-lib/aws-dynamodb';
import { ApiTableProps, BuildGlobalIndexesProps, LookUpTableProps } from './interfaces';
import {
  CONTENT_INDEX_NAME,
  CONTEXT_INDEX_NAME,
  INDEX_PARTITION_KEY,
  PACKAGING_JOB_API_GLOBAL_SECONDARY_INDEX_NAMES,
  PACKAGING_JOB_API_GLOBAL_SECONDARY_INDEX_NON_KEY_ATTRIBUTE_NAMES,
  PACKAGING_LOOKUP_TABLE_GLOBAL_SECONDARY_INDEX_NAMES_BY_INDEX,
  PUSH_JOB_API_GLOBAL_SECONDARY_INDEX_NAMES,
  PUSH_JOB_API_GLOBAL_SECONDARY_INDEX_NON_KEY_ATTRIBUTE_NAMES,
} from '../constants';

function getPackagingJobApiSecondaryIndexes(
  props: BuildGlobalIndexesProps
): GlobalSecondaryIndexPropsV2[] {
  const secondaryIndexList: GlobalSecondaryIndexPropsV2[] = [];

  for (const indexName of PACKAGING_JOB_API_GLOBAL_SECONDARY_INDEX_NAMES) {
    // Get all other elements in PACKAGING_JOB_API_GLOBAL_SECONDARY_INDEX_NAMES
    const otherIndexNames = PACKAGING_JOB_API_GLOBAL_SECONDARY_INDEX_NAMES.filter(
      (name) => name !== indexName
    );

    secondaryIndexList.push({
      indexName: `${indexName}-index`,
      partitionKey: {
        name: indexName,
        type: AttributeType.STRING,
      },
      sortKey: {
        name: props.sortKey,
        type: AttributeType.STRING,
      },
      projectionType: ProjectionType.INCLUDE,
      nonKeyAttributes: [
        ...otherIndexNames,
        ...PACKAGING_JOB_API_GLOBAL_SECONDARY_INDEX_NON_KEY_ATTRIBUTE_NAMES,
      ],
    });
  }

  return secondaryIndexList;
}

function getPushJobApiSecondaryIndexes(
  props: BuildGlobalIndexesProps
): GlobalSecondaryIndexPropsV2[] {
  const secondaryIndexList: GlobalSecondaryIndexPropsV2[] = [];

  for (const indexName of PUSH_JOB_API_GLOBAL_SECONDARY_INDEX_NAMES) {
    // Get all other elements in PACKAGING_JOB_API_GLOBAL_SECONDARY_INDEX_NAMES
    const otherIndexNames = PUSH_JOB_API_GLOBAL_SECONDARY_INDEX_NAMES.filter(
      (name) => name !== indexName
    );

    secondaryIndexList.push({
      indexName: `${indexName}-index`,
      partitionKey: {
        name: indexName,
        type: AttributeType.STRING,
      },
      sortKey: {
        name: props.sortKey,
        type: AttributeType.STRING,
      },
      projectionType: ProjectionType.INCLUDE,
      nonKeyAttributes: [
        ...otherIndexNames,
        ...PUSH_JOB_API_GLOBAL_SECONDARY_INDEX_NON_KEY_ATTRIBUTE_NAMES,
      ],
    });
  }

  return secondaryIndexList;
}

function getPackagingLookUpTableSecondaryIndexes(
  props: BuildGlobalIndexesProps
): GlobalSecondaryIndexPropsV2[] {
  const secondaryIndexList: GlobalSecondaryIndexPropsV2[] = [];

  for (const indexName of [CONTEXT_INDEX_NAME, CONTENT_INDEX_NAME]) {
    const nonKeyAttributes =
      PACKAGING_LOOKUP_TABLE_GLOBAL_SECONDARY_INDEX_NAMES_BY_INDEX[indexName];
    // Which other elements are in the list depends on which index we are building
    // Add the index to the list
    secondaryIndexList.push({
      indexName: `${indexName}-index`,
      partitionKey: {
        name: INDEX_PARTITION_KEY,
        type: AttributeType.STRING,
      },
      sortKey: {
        name: props.sortKey,
        type: AttributeType.STRING,
      },
      projectionType: ProjectionType.INCLUDE,
      nonKeyAttributes: nonKeyAttributes,
    });
  }

  return secondaryIndexList;
}

export function buildPackagingJobApiTable(scope: Construct, props: ApiTableProps) {
  // Data sharing db
  /* Create the packaging table */
  new dynamodb.TableV2(scope, props.tableName, {
    /* Either a db_uuid or an icav2 analysis id or a portal run id */
    partitionKey: {
      name: props.partitionKey,
      type: dynamodb.AttributeType.STRING,
    },
    tableName: props.tableName,
    removalPolicy: RemovalPolicy.RETAIN_ON_UPDATE_OR_DELETE,
    pointInTimeRecoverySpecification: {
      pointInTimeRecoveryEnabled: true,
    },
    globalSecondaryIndexes: getPackagingJobApiSecondaryIndexes({
      sortKey: props.partitionKey,
    }),
  });
}

export function buildPushJobApiTable(scope: Construct, props: ApiTableProps) {
  /* Create the packaging table */
  new dynamodb.TableV2(scope, props.tableName, {
    /* Either a db_uuid or an icav2 analysis id or a portal run id */
    partitionKey: {
      name: props.partitionKey,
      type: dynamodb.AttributeType.STRING,
    },
    tableName: props.tableName,
    removalPolicy: RemovalPolicy.RETAIN_ON_UPDATE_OR_DELETE,
    pointInTimeRecoverySpecification: {
      pointInTimeRecoveryEnabled: true,
    },
    globalSecondaryIndexes: getPushJobApiSecondaryIndexes({
      sortKey: props.partitionKey,
    }),
  });
}

export function buildPackagingLookUpTable(scope: Construct, props: LookUpTableProps) {
  new dynamodb.TableV2(scope, 'packaging_lookup_table', {
    /* An orcabus id of some type */
    partitionKey: {
      name: props.partitionKey,
      type: dynamodb.AttributeType.STRING,
    },
    /* 'job_id' */
    sortKey: {
      name: 'job_id',
      type: dynamodb.AttributeType.STRING,
    },
    tableName: props.tableName,
    removalPolicy: RemovalPolicy.RETAIN_ON_UPDATE_OR_DELETE,
    pointInTimeRecoverySpecification: {
      pointInTimeRecoveryEnabled: true,
    },
    // Enable TTL on the table
    timeToLiveAttribute: props.ttlAttribute,
    globalSecondaryIndexes: getPackagingLookUpTableSecondaryIndexes({
      // We want to use 'id' as the sort key for the secondary indexes
      sortKey: props.partitionKey,
    }),
  });
}
