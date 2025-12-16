import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as cdk from 'aws-cdk-lib';
import { SLACK_BOT_TOKEN_SECRET_NAME, SLACK_ALLOWED_USERS_SECRET_NAME } from '../constants';
import { Construct } from 'constructs';
import { NagSuppressions } from 'cdk-nag';

const initialAllowedUsers = JSON.stringify([
  { username: 'user1.name', id: 'U111111' },
  { username: 'user2.name', id: 'U222222' },
]);

export function createSlackSecret(scope: Construct) {
  // Slack bot token secret
  const slackBotTokenSecret = new secretsmanager.Secret(scope, 'AutoDataSharingSlackBotToken', {
    secretName: SLACK_BOT_TOKEN_SECRET_NAME,
    description: 'Slack bot token for auto-data-sharing notifications',
    secretStringValue: cdk.SecretValue.unsafePlainText('SET_AFTER_DEPLOY'),
    removalPolicy: cdk.RemovalPolicy.RETAIN,
  });

  // Slack allowed users secret (list of Slack user IDs allowed to trigger push)
  const slackAllowedUsersSecret = new secretsmanager.Secret(
    scope,
    'AutoDataSharingSlackAllowedUsers',
    {
      secretName: SLACK_ALLOWED_USERS_SECRET_NAME,
      description: 'Slack user IDs allowed to trigger auto push from Slack',
      // Initialise with an empty JSON array; you’ll edit this in the console
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
    slackAllowedUsersSecret,
    [
      {
        id: 'AwsSolutions-SMG4',
        reason: 'We dont need secrets rotation for this static allow-list.',
      },
    ],
    true
  );
}
