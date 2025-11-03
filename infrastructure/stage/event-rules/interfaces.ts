import { EventPattern, IEventBus, Rule } from 'aws-cdk-lib/aws-events';

export type EventBridgeRuleName = 'ReadSetsAdded';

export const eventBridgeRuleNameList: EventBridgeRuleName[] = ['ReadSetsAdded'];

export interface EventBridgeRuleProps {
  ruleName: EventBridgeRuleName;
  eventBus: IEventBus;
  eventPattern: EventPattern;
}

export interface EventBridgeRulesProps {
  eventBus: IEventBus;
}

export interface EventBridgeRuleObject {
  ruleName: EventBridgeRuleName;
  ruleObject: Rule;
}

export type BuildAutocontrollerFastqGlueRuleProps = Omit<EventBridgeRuleProps, 'eventPattern'>;
