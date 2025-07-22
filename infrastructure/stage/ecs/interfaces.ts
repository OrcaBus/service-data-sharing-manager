import { IBucket } from 'aws-cdk-lib/aws-s3';
import { ITableV2 } from 'aws-cdk-lib/aws-dynamodb';

export interface BuildRMarkdownFargateEcsProps {
  packagingLookUpBucket: IBucket;
  packagingLookUpPrefix: string;
  packagingLookUpTable: ITableV2;
}
