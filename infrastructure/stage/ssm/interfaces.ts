export interface AutoJob {
  name: string;
  enabled: boolean;
  projectId: string;
  shareDestination: string;
}

export interface AutoJobsFile {
  jobs: AutoJob[];
}

export interface BuildAutoJobsSsmProps {
  /** SSM prefix where each job will be written, e.g. "/umccr/data-sharing/auto-package-push" */
  ssmPrefix: string;
  /** Path to JSON file relative to this folder, e.g. "auto_package_push_jobs/dev.json" */
  jsonRelativePath: string;
}
