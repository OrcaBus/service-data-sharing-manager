import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as cdk from 'aws-cdk-lib';
import { SLACK_WEBHOOK_SECRET_NAME } from '../constants';
import { Construct } from 'constructs';
import { NagSuppressions } from 'cdk-nag';

export function createSlackSecret(scope: Construct) {
  // Create the slack webhook secret
  const slackWebhookSecret = new secretsmanager.Secret(scope, 'AutoDataSharingSlackWebhook', {
    secretName: SLACK_WEBHOOK_SECRET_NAME,
    description: 'Slack Incoming Webhook URL for auto-data-sharing notifications',
    secretStringValue: cdk.SecretValue.unsafePlainText('SET_AFTER_DEPLOY'),
    removalPolicy: cdk.RemovalPolicy.RETAIN,
  });

  // Add nag suppressions
  NagSuppressions.addResourceSuppressions(
    slackWebhookSecret,
    [
      {
        id: 'AwsSolutions-SMG4',
        reason: 'We dont need secrets rotation for this webhook URL secret.',
      },
    ],
    true
  );
}
