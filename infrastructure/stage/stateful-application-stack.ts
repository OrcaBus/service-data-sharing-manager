import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { buildDataSharingS3Bucket } from './s3';
import { StatefulApplicationStackConfig } from './interfaces';
import {
  buildPackagingJobApiTable,
  buildPackagingLookUpTable,
  buildPushJobApiTable,
} from './dynamodb';
import { createSlackSecret } from './secrets';
import { buildSsmParameters } from './ssm';

export type StatefulApplicationStackProps = cdk.StackProps & StatefulApplicationStackConfig;

export class StatefulApplicationStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: StatefulApplicationStackProps) {
    super(scope, id, props);

    /**
     * Stateful Application Stack
     * Includes:
     *   * S3 Bucket for data sharing
     *   * DynamoDB Tables for packaging jobs, push jobs, and packaging lookups
     */

    // Create the s3 bucket
    buildDataSharingS3Bucket(this, {
      bucketName: props.dataSharingBucketName,
    });

    // Generate the dynamodb tables
    buildPackagingJobApiTable(this, {
      tableName: props.packagingJobsTableName,
      partitionKey: 'id',
    });
    buildPushJobApiTable(this, {
      tableName: props.pushJobsTableName,
      partitionKey: 'id',
    });
    buildPackagingLookUpTable(this, {
      tableName: props.packagingLookUpTableName,
      partitionKey: 'id',
      sortKey: 'id_type',
      ttlAttribute: 'expire_at',
    });

    // Set SSM Parameters
    buildSsmParameters(this, props.ssmParameters);

    // Create the slack bot token secret
    createSlackSecret(this);
  }
}
