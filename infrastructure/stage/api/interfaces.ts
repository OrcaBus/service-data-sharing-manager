import { SfnObject } from '../step-functions/interfaces';
import { IEventBus } from 'aws-cdk-lib/aws-events';
import { ITableV2 } from 'aws-cdk-lib/aws-dynamodb';
import { PythonFunction, PythonLayerVersion } from '@aws-cdk/aws-lambda-python-alpha';
import { IBucket } from 'aws-cdk-lib/aws-s3';
import { IStringParameter } from 'aws-cdk-lib/aws-ssm';
import { OrcaBusApiGateway } from '@orcabus/platform-cdk-constructs/api-gateway';
import { HttpLambdaIntegration } from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import { IStateMachine } from 'aws-cdk-lib/aws-stepfunctions';

export interface LambdaApiFunctionProps {
  // Layers
  dataSharingLayer: PythonLayerVersion;
  // Step functions
  sfnObjects: SfnObject[];
  // Buckets
  packagingLookUpBucket: IBucket;
  // SSM Stuff
  hostedZoneSsmParameter: IStringParameter;
  // Event stuff
  eventBus: IEventBus;
  // Tables
  packagingDynamoDbApiTable: ITableV2;
  pushJobDynamoDbApiTable: ITableV2;
}

/** API Interfaces */
/** API Gateway interfaces **/
export interface BuildApiIntegrationProps {
  lambdaFunction: PythonFunction;
}

export interface BuildHttpRoutesProps {
  apiGateway: OrcaBusApiGateway;
  apiIntegration: HttpLambdaIntegration;
}

export interface BuildSlackAutoPushApiProps {
  autoPushSfn: IStateMachine;
}
