export interface AutoJob {
  jobName: string;
  enabled: boolean;
  projectId: string;
  shareDestination: string;
}

export interface AutoJobsFile {
  jobs: AutoJob[];
}

export interface BuildAutoJobsSsmProps {
  /** SSM prefix where each job will be written. */
  ssmPrefix: string;
  /** Path to JSON file relative to this folder. */
  jsonRelativePath: string;
}
