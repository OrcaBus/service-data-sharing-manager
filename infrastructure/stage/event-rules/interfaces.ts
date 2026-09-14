import { EventPattern, IEventBus, Rule } from 'aws-cdk-lib/aws-events';

export type EventBridgeRuleName =
  | 'ReadSetsAdded'
  | 'DataPackagingSyncRequest'
  | 'DataPackagingJobStateChange'
  | 'DataPushSyncRequest'
  | 'DataPushJobStateChange';

export const eventBridgeRuleNameList: EventBridgeRuleName[] = [
  'ReadSetsAdded',
  'DataPackagingSyncRequest',
  'DataPackagingJobStateChange',
  'DataPushSyncRequest',
  'DataPushJobStateChange',
];

export interface EventBridgeRuleProps {
  ruleName: EventBridgeRuleName;
  eventBus: IEventBus;
  eventPattern: EventPattern;
  description: string;
}

export interface EventBridgeRulesProps {
  eventBus: IEventBus;
}

export interface EventBridgeRuleObject {
  ruleName: EventBridgeRuleName;
  ruleObject: Rule;
}

export type BuildAutocontrollerFastqGlueRuleProps = Omit<
  EventBridgeRuleProps,
  'eventPattern' | 'description'
>;
