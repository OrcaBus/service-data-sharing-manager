import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as cdk from 'aws-cdk-lib';
import {
  SLACK_BOT_TOKEN_SECRET_NAME,
  SLACK_CONFIG_SECRET_NAME,
  SLACK_SIGNING_SECRET_NAME,
} from '../constants';
import { Construct } from 'constructs';
import { NagSuppressions } from 'cdk-nag';

const initialAllowedUsers = JSON.stringify({
  channel_id: 'C1234567890',
  allowed_users: [
    { username: 'user1.name', id: 'U111111' },
    { username: 'user2.name', id: 'U222222' },
  ],
});

export function createSlackSecret(scope: Construct) {
  // Slack bot token secret
  const slackBotTokenSecret = new secretsmanager.Secret(scope, 'AutoDataSharingSlackBotToken', {
    secretName: SLACK_BOT_TOKEN_SECRET_NAME,
    description: 'Slack bot token for auto-data-sharing notifications',
    secretStringValue: cdk.SecretValue.unsafePlainText('SET_AFTER_DEPLOY'),
    removalPolicy: cdk.RemovalPolicy.RETAIN,
  });

  // Slack bot token secret
  const slackSigningSecret = new secretsmanager.Secret(scope, 'AutoDataSharingSlackSigningSecret', {
    secretName: SLACK_SIGNING_SECRET_NAME,
    description: 'Slack signing secret for verifying requests to auto-data-sharing',
    secretStringValue: cdk.SecretValue.unsafePlainText('SET_AFTER_DEPLOY'),
    removalPolicy: cdk.RemovalPolicy.RETAIN,
  });

  // Slack config secret (channel_id + allowed users)
  const AutoDataSharingSlackConfig = new secretsmanager.Secret(
    scope,
    'AutoDataSharingSlackConfig',
    {
      secretName: SLACK_CONFIG_SECRET_NAME,
      description: 'Slack config: auto-data-sharing channel_id and push allowed users.',
      // Initialise with a dump JSON array. Need to be updated after deployment.
      secretStringValue: cdk.SecretValue.unsafePlainText(initialAllowedUsers),
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
