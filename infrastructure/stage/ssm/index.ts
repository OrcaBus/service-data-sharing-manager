import { Construct } from 'constructs';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import { SsmParameterProps } from './interfaces';

export function buildSsmParameters(scope: Construct, props: SsmParameterProps) {
  /**
   * SSM Stack here
   *
   * */

  /**
   * FileManager Buckets
   */
  new ssm.StringParameter(scope, 'filemanager-buckets', {
    parameterName: props.ssmParameterPaths.fileManagerBucketsList,
    stringValue: JSON.stringify(props.ssmParameterValues.fileManagerBucketsList),
  });
}
