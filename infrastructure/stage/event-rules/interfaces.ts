import { EventPattern, IEventBus, Rule } from 'aws-cdk-lib/aws-events';

export type EventBridgeRuleName = 'autocontrollerFastqGlueRowsAdded';

export const eventBridgeRuleNameList: EventBridgeRuleName[] = ['autocontrollerFastqGlueRowsAdded'];

export interface EventBridgeRuleProps {
  ruleName: EventBridgeRuleName;
  eventBus: IEventBus;
  eventPattern: EventPattern;
}

export interface EventBridgeRulesProps {
  eventBus: IEventBus;
  stage: string;
}

export interface EventBridgeRuleObject {
  ruleName: EventBridgeRuleName;
  ruleObject: Rule;
}

export type BuildAutocontrollerFastqGlueRuleProps = Omit<EventBridgeRuleProps, 'eventPattern'>;
