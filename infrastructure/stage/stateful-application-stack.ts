import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { buildDataSharingS3Bucket } from './s3';
import { StatefulApplicationStackConfig } from './interfaces';
import {
  buildPackagingJobApiTable,
  buildPackagingLookUpTable,
  buildPushJobApiTable,
} from './dynamodb';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { SLACK_WEBHOOK_SECRET_NAME } from './constants';

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
    new secretsmanager.Secret(this, 'AutoDataSharingSlackWebhook', {
      secretName: SLACK_WEBHOOK_SECRET_NAME,
      description: 'Slack Incoming Webhook URL for auto-data-sharing notifications',
      secretStringValue: cdk.SecretValue.unsafePlainText('SET_AFTER_DEPLOY'),
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });
  }
}
