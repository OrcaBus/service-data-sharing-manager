import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { DeploymentStackPipeline } from '@orcabus/platform-cdk-constructs/deployment-stack-pipeline';
import { getStatelessApplicationStackProps } from '../stage/config';
import { REPO_NAME } from './constants';
import { StatelessApplicationStack } from '../stage/stateless-application-stack';

export class StatelessStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    new DeploymentStackPipeline(this, 'StatelessDataSharingStackPipeline', {
      githubBranch: 'main',
      githubRepo: REPO_NAME,
      stack: StatelessApplicationStack,
      stackName: 'StatelessDataSharingStack',
      stackConfig: {
        beta: getStatelessApplicationStackProps('BETA'),
        gamma: getStatelessApplicationStackProps('GAMMA'),
        prod: getStatelessApplicationStackProps('PROD'),
      },
      pipelineName: 'StatelessDataSharingStackPipeline',
      cdkSynthCmd: [
        'pnpm install --frozen-lockfile --ignore-scripts',
        'pnpm cdk-stateless synth',
        // https://github.com/aws/aws-cdk/issues/21325
        // Need to keep asset.*.json though for AWS SFN Step Function Definition Bodies
        'rm -rf cdk.out/asset.*.zip',
      ],
      enableSlackNotification: false,
    });
  }
}
