import { DataSharingS3BucketProps } from './interfaces';
import { NagSuppressions } from 'cdk-nag';
import { RemovalPolicy } from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';

export function buildDataSharingS3Bucket(scope: Construct, props: DataSharingS3BucketProps) {
  /*
    Initialise s3 bucket
    Any user in the account can read and write to the bucket
    at the bucket prefix props.bucketPrefix
    */
  const bucket = new s3.Bucket(scope, props.bucketName, {
    // Generate bucket with the following name
    bucketName: props.bucketName,
    // Delete bucket when stack is deleted
    removalPolicy: RemovalPolicy.DESTROY,
    // Enforce SSL
    enforceSSL: true,
  });

  // Add in S1 suppressions for the two buckets we've created
  NagSuppressions.addResourceSuppressions(
    [bucket],
    [
      {
        id: 'AwsSolutions-S1',
        reason: 'The bucket is not publicly accessible',
      },
    ],
    true
  );
}
