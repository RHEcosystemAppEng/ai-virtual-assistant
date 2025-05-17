export interface KnowledgeBase {
  id?: string;
  name: string;
  version: string;
  embedding_model: string;
  provider_id?: string;
  vector_db_name: string;
  is_external: boolean;
  source?: string;
  source_configuration?: string;
  created_by?: string;
}

export interface Tool {
  id: string;
  name: string;
  title: string;
}

export interface Model {
  id: string;
  name: string;
  model_type: string;
}

export interface S3 {
  ACCESS_KEY_ID: string;
  SECRET_ACCESS_KEY: string;
  ENDPOINT_URL: string;
  BUCKET_NAME: string;
  REGION: string;
}

export interface GitHub {
  url: string;
  path: string;
  token: string;
  branch: string;
}
