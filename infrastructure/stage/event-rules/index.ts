/* Event Bridge Rules */
import {
  EventBridgeRuleObject,
  EventBridgeRuleProps,
  EventBridgeRulesProps,
  eventBridgeRuleNameList,
  BuildAutocontrollerFastqGlueRuleProps,
} from './interfaces';
import { EventPattern, Rule } from 'aws-cdk-lib/aws-events';
import * as events from 'aws-cdk-lib/aws-events';
import { Construct } from 'constructs';
import { AUTOCONTROLLER_RULE_NAME } from '../constants';

/* Pattern builder for orcabus.fastqglue → FastqListRowsAdded */
function buildAutocontrollerFastqGlueRowsAddedPattern(): EventPattern {
  return {
    detailType: ['FastqListRowsAdded'],
    source: ['orcabus.fastqglue'],
    detail: {
      instrumentRunId: [{ exists: true }],
    },
  };
}

function buildEventRule(
  scope: Construct,
  props: EventBridgeRuleProps,
  physicalRuleName: string
): Rule {
  return new events.Rule(scope, props.ruleName, {
    ruleName: physicalRuleName,
    eventPattern: props.eventPattern,
    eventBus: props.eventBus,
  });
}

function buildAutocontrollerFastqGlueRule(
  scope: Construct,
  props: BuildAutocontrollerFastqGlueRuleProps,
  physicalRuleName: string
): Rule {
  return buildEventRule(
    scope,
    {
      ruleName: props.ruleName,
      eventPattern: buildAutocontrollerFastqGlueRowsAddedPattern(),
      eventBus: props.eventBus,
    },
    physicalRuleName
  );
}

export function buildAllEventRules(
  scope: Construct,
  props: EventBridgeRulesProps
): EventBridgeRuleObject[] {
  const out: EventBridgeRuleObject[] = [];

  const physicalName = AUTOCONTROLLER_RULE_NAME;

  for (const ruleName of eventBridgeRuleNameList) {
    switch (ruleName) {
      case 'autocontrollerFastqGlueRowsAdded': {
        out.push({
          ruleName,
          ruleObject: buildAutocontrollerFastqGlueRule(
            scope,
            {
              ruleName,
              eventBus: props.eventBus,
            },
            physicalName
          ),
        });
        break;
      }
      // future rules: add new cases here
    }
  }

  return out;
}
