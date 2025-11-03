/* Event Bridge Rules */
import { Construct } from 'constructs';
import * as events from 'aws-cdk-lib/aws-events';
import { EventPattern, Rule } from 'aws-cdk-lib/aws-events';
import * as cdk from 'aws-cdk-lib';

import {
  AUTOCONTROLLER_RULE_DESCRIPTION,
  FASTQ_GLUE_EVENT_SOURCE,
  FASTQ_READSETS_ADDED_DETAIL_TYPE,
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
    detailType: [FASTQ_READSETS_ADDED_DETAIL_TYPE],
    source: [FASTQ_GLUE_EVENT_SOURCE],
    detail: {
      instrumentRunId: [{ exists: true }],
    },
  };
}

/* Generic rule builder */
function buildEventRule(scope: Construct, props: EventBridgeRuleProps): Rule {
  const stackPrefix = cdk.Stack.of(scope).stackName;

  return new events.Rule(scope, props.ruleName, {
    eventPattern: props.eventPattern,
    eventBus: props.eventBus,
    ruleName: `${stackPrefix}--${props.ruleName}`,
    description: AUTOCONTROLLER_RULE_DESCRIPTION,
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
      // Future rules add HERE
    }
  }

  return out;
}
