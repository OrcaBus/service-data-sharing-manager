import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as events from 'aws-cdk-lib/aws-events';
import { EventBridgeRuleObject } from '../event-rules/interfaces';
import { SfnObject } from '../step-functions/interfaces';

export type EventBridgeTargetName = 'autocontrollerFastqGlueRowsAddedToAutoControllerSfnTarget';

export const eventBridgeTargetsNameList: EventBridgeTargetName[] = [
  'autocontrollerFastqGlueRowsAddedToAutoControllerSfnTarget',
];

export interface AddSfnAsEventBridgeTargetProps {
  stateMachineObj: sfn.StateMachine;
  eventBridgeRuleObj: events.Rule;
}

export interface EventBridgeTargetsProps {
  eventBridgeRuleObjects: EventBridgeRuleObject[];
  stepFunctionObjects: SfnObject[];
}
