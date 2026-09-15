import { EventPattern, IEventBus, Rule, Schedule } from 'aws-cdk-lib/aws-events';

export type EventBridgeRuleName =
  | 'ReadSetsAdded'
  | 'DataPackagingSync'
  | 'DataPackagingJobStateChange'
  | 'DataPushSync'
  | 'DataPushJobStateChange'
  | 'SyncTokenHeartbeatSchedule';

export const eventBridgeRuleNameList: EventBridgeRuleName[] = [
  'ReadSetsAdded',
  'DataPackagingSync',
  'DataPackagingJobStateChange',
  'DataPushSync',
  'DataPushJobStateChange',
  'SyncTokenHeartbeatSchedule',
];

export interface EventBridgeRuleProps {
  ruleName: EventBridgeRuleName;
  eventBus: IEventBus;
  eventPattern: EventPattern;
  description: string;
}

export interface ScheduleRuleProps {
  ruleName: EventBridgeRuleName;
  schedule: Schedule;
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
