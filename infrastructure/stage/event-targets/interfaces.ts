import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as events from 'aws-cdk-lib/aws-events';
import { IFunction } from 'aws-cdk-lib/aws-lambda';
import { EventBridgeRuleObject } from '../event-rules/interfaces';
import { SfnObject } from '../step-functions/interfaces';
import { LambdaObject } from '../lambdas/interfaces';

export type EventBridgeTargetName =
  | 'autocontrollerFastqGlueRowsAddedToAutoControllerSfnTarget'
  | 'dataPackagingSyncToTaskTokenRecordingLambdaTarget'
  | 'dataPackagingJobStateChangeToTaskTokenResolvingLambdaTarget'
  | 'dataPushSyncToTaskTokenRecordingLambdaTarget'
  | 'dataPushJobStateChangeToTaskTokenResolvingLambdaTarget'
  | 'syncTokenHeartbeatScheduleToHeartbeatLambdaTarget';

export const eventBridgeTargetsNameList: EventBridgeTargetName[] = [
  'autocontrollerFastqGlueRowsAddedToAutoControllerSfnTarget',
  'dataPackagingSyncToTaskTokenRecordingLambdaTarget',
  'dataPackagingJobStateChangeToTaskTokenResolvingLambdaTarget',
  'dataPushSyncToTaskTokenRecordingLambdaTarget',
  'dataPushJobStateChangeToTaskTokenResolvingLambdaTarget',
  'syncTokenHeartbeatScheduleToHeartbeatLambdaTarget',
];

export interface AddSfnAsEventBridgeTargetProps {
  stateMachineObj: sfn.StateMachine;
  eventBridgeRuleObj: events.Rule;
}

export interface AddLambdaAsEventBridgeTargetProps {
  lambdaFunction: IFunction;
  eventBridgeRuleObj: events.Rule;
}

export interface EventBridgeTargetsProps {
  eventBridgeRuleObjects: EventBridgeRuleObject[];
  stepFunctionObjects: SfnObject[];
  lambdaObjects: LambdaObject[];
}
