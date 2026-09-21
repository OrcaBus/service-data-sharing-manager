export interface BuildGlobalIndexesProps {
  sortKey: string;
}

export interface ApiTableProps {
  tableName: string;
  partitionKey: string;
}

export interface LookUpTableProps {
  tableName: string;
  partitionKey: string;
  sortKey: string;
  ttlAttribute: string;
}

export interface TaskTokenTableProps {
  tableName: string;
  partitionKey: string;
  ttlAttribute: string;
}
