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
        const rule = props.eventBridgeRuleObjects.find(
          (eventRuleIter) => eventRuleIter.ruleName === 'ReadSetsAdded'
        )?.ruleObject;
        const stateMachine = props.stepFunctionObjects.find(
          (sfnIter) => sfnIter.stateMachineName === 'autoController'
        )?.stateMachineObj;

        if (!rule || !stateMachine) {
          throw new Error('Required rule or state machine not found');
        }

        buildAutocontrollerFastqGlueToAutoControllerSfnTarget({
          eventBridgeRuleObj: rule,
          stateMachineObj: stateMachine,
        });
        break;
      }
    }
  }
}
