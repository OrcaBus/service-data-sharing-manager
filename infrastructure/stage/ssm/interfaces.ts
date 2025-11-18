export interface SsmParameterValues {
  // Payload defaults
  fileManagerBucketsList: string[];
}

export interface SsmParameterPaths {
  fileManagerBucketsList: string;
}

export interface SsmParameterProps {
  ssmParameterValues: SsmParameterValues;
  ssmParameterPaths: SsmParameterPaths;
}
