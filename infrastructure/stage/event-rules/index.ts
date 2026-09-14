/* Event Bridge Rules */
import { Construct } from 'constructs';
import * as events from 'aws-cdk-lib/aws-events';
import { EventPattern, Rule } from 'aws-cdk-lib/aws-events';

import {
  AUTOCONTROLLER_RULE_DESCRIPTION,
  FASTQ_GLUE_EVENT_SOURCE,
  PACKAGING_JOB_STATE_CHANGE_EVENT_DETAIL_TYPE,
  PACKAGING_JOB_STATE_CHANGE_RULE_DESCRIPTION,
  PACKAGING_SYNC_REQUEST_DETAIL_TYPE,
  PACKAGING_SYNC_REQUEST_RULE_DESCRIPTION,
  PUSH_JOB_STATE_CHANGE_EVENT_DETAIL_TYPE,
  PUSH_JOB_STATE_CHANGE_RULE_DESCRIPTION,
  PUSH_SYNC_REQUEST_DETAIL_TYPE,
  PUSH_SYNC_REQUEST_RULE_DESCRIPTION,
  READSETS_ADDED_DETAIL_TYPE,
  STACK_PREFIX,
  STACK_SOURCE,
} from '../constants';
import {
  EventBridgeRuleObject,
  EventBridgeRuleProps,
  EventBridgeRulesProps,
  BuildAutocontrollerFastqGlueRuleProps,
  eventBridgeRuleNameList,
} from './interfaces';

/* Pattern builder */
function buildAutocontrollerFastqGlueRowsAddedPattern(): EventPattern {
  return {
    detailType: [READSETS_ADDED_DETAIL_TYPE],
    source: [FASTQ_GLUE_EVENT_SOURCE],
    detail: {
      instrumentRunId: [{ exists: true }],
    },
  };
}

function buildPackagingSyncRequestPattern(): EventPattern {
  return {
    detailType: [PACKAGING_SYNC_REQUEST_DETAIL_TYPE],
    source: [STACK_SOURCE],
  };
}

function buildPackagingJobStateChangePattern(): EventPattern {
  return {
    detailType: [PACKAGING_JOB_STATE_CHANGE_EVENT_DETAIL_TYPE],
    source: [STACK_SOURCE],
  };
}

function buildPushSyncRequestPattern(): EventPattern {
  return {
    detailType: [PUSH_SYNC_REQUEST_DETAIL_TYPE],
    source: [STACK_SOURCE],
  };
}

function buildPushJobStateChangePattern(): EventPattern {
  return {
    detailType: [PUSH_JOB_STATE_CHANGE_EVENT_DETAIL_TYPE],
    source: [STACK_SOURCE],
  };
}

/* Generic rule builder */
function buildEventRule(scope: Construct, props: EventBridgeRuleProps): Rule {
  return new events.Rule(scope, props.ruleName, {
    eventPattern: props.eventPattern,
    eventBus: props.eventBus,
    ruleName: `${STACK_PREFIX}--${props.ruleName}`,
    description: props.description,
  });
}

/* Specific builder for the autocontroller FastqGlue rule */
function buildAutocontrollerFastqGlueRule(
  scope: Construct,
  props: BuildAutocontrollerFastqGlueRuleProps
): Rule {
  return buildEventRule(scope, {
    ruleName: props.ruleName,
    eventPattern: buildAutocontrollerFastqGlueRowsAddedPattern(),
    eventBus: props.eventBus,
    description: AUTOCONTROLLER_RULE_DESCRIPTION,
  });
}

/* Build all declared rules from interfaces.ts */
export function buildAllEventRules(
  scope: Construct,
  props: EventBridgeRulesProps
): EventBridgeRuleObject[] {
  const out: EventBridgeRuleObject[] = [];

  for (const ruleName of eventBridgeRuleNameList) {
    switch (ruleName) {
      case 'ReadSetsAdded': {
        out.push({
          ruleName,
          ruleObject: buildAutocontrollerFastqGlueRule(scope, {
            ruleName,
            eventBus: props.eventBus,
          }),
        });
        break;
      }
      case 'DataPackagingSyncRequest': {
        out.push({
          ruleName,
          ruleObject: buildEventRule(scope, {
            ruleName,
            eventPattern: buildPackagingSyncRequestPattern(),
            eventBus: props.eventBus,
            description: PACKAGING_SYNC_REQUEST_RULE_DESCRIPTION,
          }),
        });
        break;
      }
      case 'DataPackagingJobStateChange': {
        out.push({
          ruleName,
          ruleObject: buildEventRule(scope, {
            ruleName,
            eventPattern: buildPackagingJobStateChangePattern(),
            eventBus: props.eventBus,
            description: PACKAGING_JOB_STATE_CHANGE_RULE_DESCRIPTION,
          }),
        });
        break;
      }
      case 'DataPushSyncRequest': {
        out.push({
          ruleName,
          ruleObject: buildEventRule(scope, {
            ruleName,
            eventPattern: buildPushSyncRequestPattern(),
            eventBus: props.eventBus,
            description: PUSH_SYNC_REQUEST_RULE_DESCRIPTION,
          }),
        });
        break;
      }
      case 'DataPushJobStateChange': {
        out.push({
          ruleName,
          ruleObject: buildEventRule(scope, {
            ruleName,
            eventPattern: buildPushJobStateChangePattern(),
            eventBus: props.eventBus,
            description: PUSH_JOB_STATE_CHANGE_RULE_DESCRIPTION,
          }),
        });
        break;
      }
      // Future rules add HERE
    }
  }

  return out;
}
