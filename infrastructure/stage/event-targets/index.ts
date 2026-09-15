import {
  AddLambdaAsEventBridgeTargetProps,
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

export function buildDataPackagingSyncToTaskTokenRecordingLambdaTarget(
  props: AddLambdaAsEventBridgeTargetProps
) {
  props.eventBridgeRuleObj.addTarget(
    new eventsTargets.LambdaFunction(props.lambdaFunction, {
      event: events.RuleTargetInput.fromEventPath('$.detail'),
    })
  );
}

export function buildDataPackagingJobStateChangeToTaskTokenResolvingLambdaTarget(
  props: AddLambdaAsEventBridgeTargetProps
) {
  props.eventBridgeRuleObj.addTarget(
    new eventsTargets.LambdaFunction(props.lambdaFunction, {
      event: events.RuleTargetInput.fromEventPath('$.detail'),
    })
  );
}

export function buildDataPushSyncToTaskTokenRecordingLambdaTarget(
  props: AddLambdaAsEventBridgeTargetProps
) {
  props.eventBridgeRuleObj.addTarget(
    new eventsTargets.LambdaFunction(props.lambdaFunction, {
      event: events.RuleTargetInput.fromEventPath('$.detail'),
    })
  );
}

export function buildDataPushJobStateChangeToTaskTokenResolvingLambdaTarget(
  props: AddLambdaAsEventBridgeTargetProps
) {
  props.eventBridgeRuleObj.addTarget(
    new eventsTargets.LambdaFunction(props.lambdaFunction, {
      event: events.RuleTargetInput.fromEventPath('$.detail'),
    })
  );
}

export function buildSyncTokenHeartbeatScheduleToHeartbeatLambdaTarget(
  props: AddLambdaAsEventBridgeTargetProps
) {
  props.eventBridgeRuleObj.addTarget(new eventsTargets.LambdaFunction(props.lambdaFunction));
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
      case 'dataPackagingSyncToTaskTokenRecordingLambdaTarget': {
        const rule = props.eventBridgeRuleObjects.find(
          (eventRuleIter) => eventRuleIter.ruleName === 'DataPackagingSync'
        )?.ruleObject;
        const lambdaFunction = props.lambdaObjects.find(
          (lambdaIter) => lambdaIter.lambdaName === 'taskTokenTriggerJobAndTrack'
        )?.lambdaFunction;

        if (!rule || !lambdaFunction) {
          throw new Error('Required rule or lambda function not found');
        }

        buildDataPackagingSyncToTaskTokenRecordingLambdaTarget({
          eventBridgeRuleObj: rule,
          lambdaFunction: lambdaFunction,
        });
        break;
      }
      case 'dataPackagingJobStateChangeToTaskTokenResolvingLambdaTarget': {
        const rule = props.eventBridgeRuleObjects.find(
          (eventRuleIter) => eventRuleIter.ruleName === 'DataPackagingJobStateChange'
        )?.ruleObject;
        const lambdaFunction = props.lambdaObjects.find(
          (lambdaIter) => lambdaIter.lambdaName === 'taskTokenResolve'
        )?.lambdaFunction;

        if (!rule || !lambdaFunction) {
          throw new Error('Required rule or lambda function not found');
        }

        buildDataPackagingJobStateChangeToTaskTokenResolvingLambdaTarget({
          eventBridgeRuleObj: rule,
          lambdaFunction: lambdaFunction,
        });
        break;
      }
      case 'dataPushSyncToTaskTokenRecordingLambdaTarget': {
        const rule = props.eventBridgeRuleObjects.find(
          (eventRuleIter) => eventRuleIter.ruleName === 'DataPushSync'
        )?.ruleObject;
        const lambdaFunction = props.lambdaObjects.find(
          (lambdaIter) => lambdaIter.lambdaName === 'taskTokenTriggerJobAndTrack'
        )?.lambdaFunction;

        if (!rule || !lambdaFunction) {
          throw new Error('Required rule or lambda function not found');
        }

        buildDataPushSyncToTaskTokenRecordingLambdaTarget({
          eventBridgeRuleObj: rule,
          lambdaFunction: lambdaFunction,
        });
        break;
      }
      case 'dataPushJobStateChangeToTaskTokenResolvingLambdaTarget': {
        const rule = props.eventBridgeRuleObjects.find(
          (eventRuleIter) => eventRuleIter.ruleName === 'DataPushJobStateChange'
        )?.ruleObject;
        const lambdaFunction = props.lambdaObjects.find(
          (lambdaIter) => lambdaIter.lambdaName === 'taskTokenResolve'
        )?.lambdaFunction;

        if (!rule || !lambdaFunction) {
          throw new Error('Required rule or lambda function not found');
        }

        buildDataPushJobStateChangeToTaskTokenResolvingLambdaTarget({
          eventBridgeRuleObj: rule,
          lambdaFunction: lambdaFunction,
        });
        break;
      }
      case 'syncTokenHeartbeatScheduleToHeartbeatLambdaTarget': {
        const rule = props.eventBridgeRuleObjects.find(
          (eventRuleIter) => eventRuleIter.ruleName === 'SyncTokenHeartbeatSchedule'
        )?.ruleObject;
        const lambdaFunction = props.lambdaObjects.find(
          (lambdaIter) => lambdaIter.lambdaName === 'taskTokenHeartbeat'
        )?.lambdaFunction;

        if (!rule || !lambdaFunction) {
          throw new Error('Required rule or lambda function not found');
        }

        buildSyncTokenHeartbeatScheduleToHeartbeatLambdaTarget({
          eventBridgeRuleObj: rule,
          lambdaFunction: lambdaFunction,
        });
        break;
      }
    }
  }
}
