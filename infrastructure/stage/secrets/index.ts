import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as cdk from 'aws-cdk-lib';
import {
  SLACK_BOT_TOKEN_SECRET_NAME,
  SLACK_CONFIG_SECRET_NAME,
  SLACK_SIGNING_SECRET_NAME,
} from '../constants';
import { Construct } from 'constructs';
import { NagSuppressions } from 'cdk-nag';

export function createSlackSecret(scope: Construct) {
  // Slack bot token secret
  const slackBotTokenSecret = new secretsmanager.Secret(scope, 'AutoDataSharingSlackBotToken', {
    secretName: SLACK_BOT_TOKEN_SECRET_NAME,
    description: 'Slack bot token for auto-data-sharing notifications',
    removalPolicy: cdk.RemovalPolicy.RETAIN,
  });

  // Slack signing secret
  const slackSigningSecret = new secretsmanager.Secret(scope, 'AutoDataSharingSlackSigningSecret', {
    secretName: SLACK_SIGNING_SECRET_NAME,
    description: 'Slack signing secret for verifying requests to auto-data-sharing',
    removalPolicy: cdk.RemovalPolicy.RETAIN,
  });

  // Slack config secret (channel_id + allowed users)
  const AutoDataSharingSlackConfig = new secretsmanager.Secret(
    scope,
    'AutoDataSharingSlackConfig',
    {
      secretName: SLACK_CONFIG_SECRET_NAME,
      description: 'Slack config: auto-data-sharing channel_id and push allowed users.',
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    }
  );

  // Add nag suppressions
  NagSuppressions.addResourceSuppressions(
    slackBotTokenSecret,
    [
      {
        id: 'AwsSolutions-SMG4',
        reason: 'We dont need secrets rotation for this token.',
      },
    ],
    true
  );

  NagSuppressions.addResourceSuppressions(
    slackSigningSecret,
    [
      {
        id: 'AwsSolutions-SMG4',
        reason: 'We dont need secrets rotation for this token.',
      },
    ],
    true
  );

  NagSuppressions.addResourceSuppressions(
    AutoDataSharingSlackConfig,
    [
      {
        id: 'AwsSolutions-SMG4',
        reason: 'We dont need secrets rotation for this static allow-list.',
      },
    ],
    true
  );
}
