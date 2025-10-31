import {
  AddSfnAsEventBridgeTargetProps,
  eventBridgeTargetsNameList,
  EventBridgeTargetsProps,
} from './interfaces';
import * as eventsTargets from 'aws-cdk-lib/aws-events-targets';
import * as events from 'aws-cdk-lib/aws-events';
import { Construct } from 'constructs';

export function buildAutocontrollerFastqGlueToAutoControllerSfnTarget(
  props: AddSfnAsEventBridgeTargetProps
) {
  props.eventBridgeRuleObj.addTarget(
    new eventsTargets.SfnStateMachine(props.stateMachineObj, {
      input: events.RuleTargetInput.fromEventPath('$.detail'),
    })
  );
}

export function buildAllEventBridgeTargets(_scope: Construct, props: EventBridgeTargetsProps) {
  for (const targetName of eventBridgeTargetsNameList) {
    switch (targetName) {
      case 'autocontrollerFastqGlueRowsAddedToAutoControllerSfnTarget': {
        buildAutocontrollerFastqGlueToAutoControllerSfnTarget({
          eventBridgeRuleObj: props.eventBridgeRuleObjects.find(
            (o) => o.ruleName === 'autocontrollerFastqGlueRowsAdded'
          )!.ruleObject,
          stateMachineObj: props.stepFunctionObjects.find(
            (o) => o.stateMachineName === 'autoController'
          )!.stateMachineObj,
        });
        break;
      }
    }
  }
}
