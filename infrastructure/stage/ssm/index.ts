import { Construct } from 'constructs';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import * as fs from 'fs';
import * as path from 'path';
import { AutoJobsFile, BuildAutoJobsSsmProps } from './interfaces';

/**
 * Create one SSM parameter per auto-package-push job from a JSON file.
 * Keeps it consistent with your other repo's "buildSsmParameters" style.
 */
export function buildAutoPackagePushJobParameters(scope: Construct, props: BuildAutoJobsSsmProps) {
  const jsonPath = path.join(__dirname, props.jsonRelativePath);
  const parsed = JSON.parse(fs.readFileSync(jsonPath, 'utf8')) as AutoJobsFile;

  for (const job of parsed.jobs ?? []) {
    new ssm.StringParameter(scope, `auto-job-${job.jobName}`, {
      parameterName: `${props.ssmPrefix}/${job.jobName}`,
      stringValue: JSON.stringify(job),
    });
  }
}
