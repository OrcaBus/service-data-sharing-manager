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
            (eventRuleIter) => eventRuleIter.ruleName === 'ReadSetsAdded'
          )!.ruleObject,
          stateMachineObj: props.stepFunctionObjects.find(
            (sfnIter) => sfnIter.stateMachineName === 'autoController'
          )!.stateMachineObj,
        });
        break;
      }
    }
  }
}
