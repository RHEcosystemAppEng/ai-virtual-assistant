import { useForm } from '@tanstack/react-form';
import { EmbeddingModel, KnowledgeBase, Provider } from '@/types';
import {
  Button,
  ActionGroup,
  Form,
  FormGroup,
  TextInput,
  Alert,
  Accordion,
  AccordionItem,
  AccordionContent,
  AccordionToggle,
  CodeBlock,
  CodeBlockCode,
} from '@patternfly/react-core';
import {
  FormSelect,
  FormSelectOption,
} from '@patternfly/react-core/dist/esm/components/FormSelect';
import { Fragment, useState, useEffect } from 'react';
import { PaperPlaneIcon, TrashIcon } from '@patternfly/react-icons';

// Form data type - same as KnowledgeBase with additional source configuration fields
type KnowledgeBaseFormData = KnowledgeBase & {
  s3_access_key_id?: string;
  s3_secret_access_key?: string;
  s3_endpoint_url?: string;
  s3_bucket_name?: string;
  s3_region?: string;
  github_url?: string;
  github_path?: string;
  github_token?: string;
  github_branch?: string;
};

// Define source options at the top for easy configuration
const KB_SOURCE_OPTIONS = [
  { value: '', label: 'Select a source', disabled: true },
  { value: 'S3', label: 'S3', disabled: false },
  { value: 'GITHUB', label: 'GITHUB', disabled: false },
  { value: 'URL', label: 'URL', disabled: false },
];

interface EmbeddingModelsFieldProps {
  models: EmbeddingModel[];
  isLoadingModels: boolean;
  modelsError: Error | null;
}

interface ProvidersFieldProps {
  providers: Provider[];
  isLoadingProviders: boolean;
  providersError: Error | null;
}

interface KnowledgeBaseFormProps {
  embeddingModelProps: EmbeddingModelsFieldProps;
  providersProps: ProvidersFieldProps;
  defaultKnowledgeBase?: KnowledgeBase;
  isSubmitting: boolean;
  onSubmit: (values: KnowledgeBase) => void;
  onCancel: () => void;
  error?: Error | null;
}

export function KnowledgeBaseForm({
  embeddingModelProps,
  providersProps,
  defaultKnowledgeBase,
  isSubmitting,
  onSubmit,
  onCancel,
  error,
}: KnowledgeBaseFormProps) {
  const { models, isLoadingModels, modelsError } = embeddingModelProps;
  const { providers, isLoadingProviders, providersError } = providersProps;

  // State for URL inputs (special case since it's an array)
  const [urlInputs, setUrlInputs] = useState<string[]>(['']);
  const [urlErrors, setUrlErrors] = useState<(string | undefined)[]>(['']);
  const [defaultVectorDbName, setDefaultVectorDbName] = useState<string>('');

  // State for configuration preview
  const [isPreviewExpanded, setIsPreviewExpanded] = useState(false);

  // Validation functions
  const validateS3Field = (fieldName: string, value: string): string | undefined => {
    switch (fieldName) {
      case 'ACCESS_KEY_ID':
        if (!value.trim()) return 'Access Key ID is required';
        return undefined;
      case 'SECRET_ACCESS_KEY':
        if (!value.trim()) return 'Secret Access Key is required';
        return undefined;
      case 'ENDPOINT_URL':
        if (!value.trim()) return 'Endpoint URL is required';
        try {
          new URL(value);
          if (!value.startsWith('https://')) return 'Endpoint URL should use HTTPS';
        } catch {
          return 'Please enter a valid URL';
        }
        return undefined;
      case 'BUCKET_NAME':
        if (!value.trim()) return 'Bucket name is required';
        return undefined;
      case 'REGION':
        if (!value.trim()) return 'Region is required';
        if (!/^[a-z0-9-]+$/.test(value))
          return 'Region should contain only lowercase letters, numbers, and hyphens';
        return undefined;
      default:
        return undefined;
    }
  };

  const validateGithubField = (fieldName: string, value: string): string | undefined => {
    switch (fieldName) {
      case 'url':
        if (!value.trim()) return 'Repository URL is required';
        try {
          const url = new URL(value);
          if (!url.hostname.includes('github.com')) return 'Must be a GitHub repository URL';
          if (!value.match(/github\.com\/[\w.-]+\/[\w.-]+/))
            return 'Invalid GitHub repository format';
        } catch {
          return 'Please enter a valid URL';
        }
        return undefined;
      case 'path':
        // Path is optional, but if provided should be valid
        if (value && (value.includes('..') || value.startsWith('/'))) {
          return 'Path should be relative and not contain ".."';
        }
        return undefined;
      case 'token':
        // Token is optional for public repos
        if (value && (value.length < 10 || !/^[a-zA-Z0-9_]+$/.test(value))) {
          return 'Invalid token format';
        }
        return undefined;
      case 'branch':
        // Branch is optional, defaults to main
        if (value && !/^[a-zA-Z0-9/_.-]+$/.test(value)) {
          return 'Invalid branch name format';
        }
        return undefined;
      default:
        return undefined;
    }
  };

  const validateUrl = (url: string): string | undefined => {
    if (!url.trim()) return 'URL is required';
    try {
      new URL(url);
      if (!url.startsWith('http://') && !url.startsWith('https://')) {
        return 'URL must start with http:// or https://';
      }
    } catch {
      return 'Please enter a valid URL';
    }
    return undefined;
  };

  const initialData: KnowledgeBaseFormData = defaultKnowledgeBase
    ? {
        ...defaultKnowledgeBase,
      }
    : {
        name: '',
        version: '',
        embedding_model: '',
        provider_id: '',
        vector_db_name: '',
        is_external: false,
        source: '',
        source_configuration: {},
        // Individual source configuration fields
        s3_access_key_id: '',
        s3_secret_access_key: '',
        s3_endpoint_url: '',
        s3_bucket_name: '',
        s3_region: '',
        github_url: '',
        github_path: '',
        github_token: '',
        github_branch: '',
      };

  const form = useForm({
    defaultValues: initialData,
    onSubmit: ({ value }) => {
      // Transform individual source configuration fields into the source_configuration object
      let finalValue: KnowledgeBase;

      if (value.source === 'S3') {
        finalValue = {
          ...value,
          source_configuration: {
            ACCESS_KEY_ID: value.s3_access_key_id || '',
            SECRET_ACCESS_KEY: value.s3_secret_access_key || '',
            ENDPOINT_URL: value.s3_endpoint_url || '',
            BUCKET_NAME: value.s3_bucket_name || '',
            REGION: value.s3_region || '',
          },
        };
      } else if (value.source === 'GITHUB') {
        finalValue = {
          ...value,
          source_configuration: {
            url: value.github_url || '',
            path: value.github_path || '',
            token: value.github_token || '',
            branch: value.github_branch || '',
          },
        };
      } else if (value.source === 'URL') {
        // For URLs, use the array directly
        const filteredUrls = urlInputs.filter((url) => url.trim() !== '');
        finalValue = {
          ...value,
          source_configuration: filteredUrls as unknown as Record<string, unknown>,
        };
      } else {
        finalValue = value;
      }

      if (finalValue.vector_db_name.trim() === '') {
        finalValue.vector_db_name = defaultVectorDbName;
      }

      // Remove the individual source fields from the final value
      const {
        s3_access_key_id: _s3_access_key_id,
        s3_secret_access_key: _s3_secret_access_key,
        s3_endpoint_url: _s3_endpoint_url,
        s3_bucket_name: _s3_bucket_name,
        s3_region: _s3_region,
        github_url: _github_url,
        github_path: _github_path,
        github_token: _github_token,
        github_branch: _github_branch,
        ...cleanValue
      } = finalValue as unknown as Record<string, unknown>;

      onSubmit(cleanValue as unknown as KnowledgeBase);
    },
  });

  // Initialize structured inputs when defaultKnowledgeBase changes
  useEffect(() => {
    if (defaultKnowledgeBase?.source_configuration) {
      const config = defaultKnowledgeBase.source_configuration;
      if (
        defaultKnowledgeBase.source === 'S3' &&
        typeof config === 'object' &&
        !Array.isArray(config)
      ) {
        const s3Config = config as Record<string, string>;
        form.setFieldValue('s3_access_key_id', s3Config.ACCESS_KEY_ID || '');
        form.setFieldValue('s3_secret_access_key', s3Config.SECRET_ACCESS_KEY || '');
        form.setFieldValue('s3_endpoint_url', s3Config.ENDPOINT_URL || '');
        form.setFieldValue('s3_bucket_name', s3Config.BUCKET_NAME || '');
        form.setFieldValue('s3_region', s3Config.REGION || '');
      } else if (
        defaultKnowledgeBase.source === 'GITHUB' &&
        typeof config === 'object' &&
        !Array.isArray(config)
      ) {
        const githubConfig = config as Record<string, string>;
        form.setFieldValue('github_url', githubConfig.url || '');
        form.setFieldValue('github_path', githubConfig.path || '');
        form.setFieldValue('github_token', githubConfig.token || '');
        form.setFieldValue('github_branch', githubConfig.branch || '');
      } else if (defaultKnowledgeBase.source === 'URL' && Array.isArray(config)) {
        setUrlInputs(config as string[]);
      }
    }
  }, [defaultKnowledgeBase, form]);

  // Generate preview of the configuration JSON
  const generatePreviewJson = () => {
    const currentValues = form.state.values;
    const previewConfig: Record<string, unknown> = {
      name: currentValues.name || '',
      version: currentValues.version || '',
      embedding_model: currentValues.embedding_model || '',
      provider_id: currentValues.provider_id || '',
      vector_db_name: currentValues.vector_db_name || '',
      is_external: currentValues.is_external || false,
      source: currentValues.source || '',
      source_configuration: {},
    };

    // Build source_configuration based on selected source
    if (currentValues.source === 'S3') {
      previewConfig.source_configuration = {
        ACCESS_KEY_ID: currentValues.s3_access_key_id || '',
        SECRET_ACCESS_KEY: currentValues.s3_secret_access_key || '',
        ENDPOINT_URL: currentValues.s3_endpoint_url || '',
        BUCKET_NAME: currentValues.s3_bucket_name || '',
        REGION: currentValues.s3_region || '',
      };
    } else if (currentValues.source === 'GITHUB') {
      previewConfig.source_configuration = {
        url: currentValues.github_url || '',
        path: currentValues.github_path || '',
        token: currentValues.github_token || '',
        branch: currentValues.github_branch || '',
      };
    } else if (currentValues.source === 'URL') {
      const filteredUrls = urlInputs.filter((url) => url.trim() !== '');
      previewConfig.source_configuration = filteredUrls;
    }

    return JSON.stringify(previewConfig, null, 2);
  };

  const buildDefaultVectorDbName = () => {
    const name = form.getFieldValue('name')?.trim() || '';
    const version = form.getFieldValue('version')?.trim() || '';
    const env = form.getFieldValue('source')?.trim() || '';

    const parts = [name, version, env].filter(Boolean);
    const dbname = parts.join('-').toLowerCase();

    setDefaultVectorDbName(dbname);
  };

  return (
    <Form
      onSubmit={(e) => {
        e.preventDefault();
        e.stopPropagation();
        void form.handleSubmit();
      }}
    >
      {error && <Alert variant="danger" title={error.message} />}
      <form.Field
        name="name"
        validators={{ onChange: ({ value }) => (!value ? 'Name is required' : undefined) }}
      >
        {(field) => (
          <FormGroup label="Name" isRequired fieldId="kb-form-name">
            <TextInput
              isRequired
              id="kb-form-name"
              value={field.state.value}
              onChange={(_e, v) => {
                field.handleChange(v);
                buildDefaultVectorDbName();
              }}
              validated={
                !field.state.meta.isTouched
                  ? 'default'
                  : field.state.meta.errors.length > 0
                    ? 'error'
                    : 'success'
              }
            />
          </FormGroup>
        )}
      </form.Field>
      <form.Field
        name="version"
        validators={{ onChange: ({ value }) => (!value ? 'Version is required' : undefined) }}
      >
        {(field) => (
          <FormGroup label="Version" isRequired fieldId="kb-form-version">
            <TextInput
              isRequired
              id="kb-form-version"
              value={field.state.value}
              onChange={(_e, v) => {
                field.handleChange(v);
                buildDefaultVectorDbName();
              }}
              validated={
                !field.state.meta.isTouched
                  ? 'default'
                  : field.state.meta.errors.length > 0
                    ? 'error'
                    : 'success'
              }
            />
          </FormGroup>
        )}
      </form.Field>
      <form.Field
        name="embedding_model"
        validators={{
          onChange: ({ value }) => (!value ? 'Embedding Model is required' : undefined),
        }}
      >
        {(field) => (
          <FormGroup label="Embedding Model" isRequired fieldId="kb-form-embedding-model">
            <FormSelect
              isRequired
              id="kb-form-embedding-model"
              name={field.name}
              value={field.state.value}
              onBlur={field.handleBlur}
              onChange={(_event, value) => field.handleChange(value)}
              aria-label="Select Embedding Model"
              validated={
                !field.state.meta.isTouched
                  ? 'default'
                  : field.state.meta.errors.length > 0
                    ? 'error'
                    : 'success'
              }
            >
              {isLoadingModels ? (
                <FormSelectOption key="loading" value="" label="Loading models..." isDisabled />
              ) : modelsError ? (
                <FormSelectOption key="error" value="" label="Error loading models" isDisabled />
              ) : (
                <Fragment>
                  <FormSelectOption key="placeholder" value="" label="Select a model" isDisabled />
                  {models.map((opt) => (
                    <FormSelectOption key={opt.name} value={opt.name} label={opt.name} />
                  ))}
                </Fragment>
              )}
            </FormSelect>
          </FormGroup>
        )}
      </form.Field>
      <form.Field
        name="provider_id"
        validators={{ onChange: ({ value }) => (!value ? 'Provider ID is required' : undefined) }}
      >
        {(field) => (
          <FormGroup label="Provider" isRequired fieldId="kb-form-provider-id">
            <FormSelect
              isRequired
              id="kb-form-provider-id"
              name={field.name}
              value={field.state.value}
              onBlur={field.handleBlur}
              onChange={(_event, value) => field.handleChange(value)}
              aria-label="Select Provider"
              validated={
                !field.state.meta.isTouched
                  ? 'default'
                  : field.state.meta.errors.length > 0
                    ? 'error'
                    : 'success'
              }
            >
              {isLoadingProviders ? (
                <FormSelectOption key="loading" value="" label="Loading providers..." isDisabled />
              ) : providersError ? (
                <FormSelectOption key="error" value="" label="Error loading providers" isDisabled />
              ) : (
                <Fragment>
                  <FormSelectOption
                    key="placeholder"
                    value=""
                    label="Select a provider"
                    isDisabled
                  />
                  {providers
                    .filter((p) => p.api === 'vector_io')
                    .map((provider) => (
                      <FormSelectOption
                        key={provider.provider_id}
                        value={provider.provider_id}
                        label={`${provider.provider_id} (${provider.provider_type})`}
                      />
                    ))}
                </Fragment>
              )}
            </FormSelect>
          </FormGroup>
        )}
      </form.Field>
      <form.Field
        name="vector_db_name"
      >
        {(field) => (
          <FormGroup label="Vector DB Name" fieldId="kb-form-vector-db-name">
            <TextInput
              id="kb-form-vector-db-name"
              value={field.state.value}
              placeholder={defaultVectorDbName}
              onChange={(_e, v) => field.handleChange(v)}
            />
          </FormGroup>
        )}
      </form.Field>
      <form.Field
        name="source"
        validators={{ onChange: ({ value }) => (!value ? 'Source is required' : undefined) }}
      >
        {(field) => (
          <FormGroup label="Source" isRequired fieldId="kb-form-source">
            <FormSelect
              isRequired
              id="kb-form-source"
              name={field.name}
              value={field.state.value}
              onBlur={field.handleBlur}
              onChange={(_event, value) => {
                field.handleChange(value);
                // Reset URL inputs when source changes
                if (value === 'URL') {
                  setUrlInputs(['']);
                }
                buildDefaultVectorDbName();
              }}
              aria-label="Select Source"
              validated={
                !field.state.meta.isTouched
                  ? 'default'
                  : field.state.meta.errors.length > 0
                    ? 'error'
                    : 'success'
              }
            >
              {KB_SOURCE_OPTIONS.map((opt) => (
                <FormSelectOption
                  key={opt.value}
                  value={opt.value}
                  label={opt.label}
                  isDisabled={opt.disabled}
                />
              ))}
            </FormSelect>
          </FormGroup>
        )}
      </form.Field>

      {/* Source Configuration Fields - Subscribe to source changes for reactive rendering */}
      <form.Subscribe selector={(state) => [state.values.source]}>
        {([source]) => (
          <>
            {/* S3 Configuration Fields */}
            {source === 'S3' && (
              <>
                <form.Field
                  name="s3_access_key_id"
                  validators={{
                    onChange: ({ value }) => validateS3Field('ACCESS_KEY_ID', value || ''),
                  }}
                >
                  {(field) => (
                    <FormGroup label="ACCESS_KEY_ID" isRequired fieldId="kb-form-s3-access-key">
                      <TextInput
                        isRequired
                        id="kb-form-s3-access-key"
                        value={field.state.value || ''}
                        onChange={(_e, v) => field.handleChange(v)}
                        placeholder="Your access key ID"
                        validated={
                          !field.state.meta.isTouched
                            ? 'default'
                            : field.state.meta.errors.length > 0
                              ? 'error'
                              : 'success'
                        }
                      />
                      {field.state.meta.errors.length > 0 && (
                        <div style={{ color: '#c9190b', fontSize: '14px', marginTop: '4px' }}>
                          {field.state.meta.errors[0]}
                        </div>
                      )}
                    </FormGroup>
                  )}
                </form.Field>
                <form.Field
                  name="s3_secret_access_key"
                  validators={{
                    onChange: ({ value }) => validateS3Field('SECRET_ACCESS_KEY', value || ''),
                  }}
                >
                  {(field) => (
                    <FormGroup label="SECRET_ACCESS_KEY" isRequired fieldId="kb-form-s3-secret-key">
                      <TextInput
                        isRequired
                        type="password"
                        id="kb-form-s3-secret-key"
                        value={field.state.value || ''}
                        onChange={(_e, v) => field.handleChange(v)}
                        placeholder="Your secret access key"
                        validated={
                          !field.state.meta.isTouched
                            ? 'default'
                            : field.state.meta.errors.length > 0
                              ? 'error'
                              : 'success'
                        }
                      />
                      {field.state.meta.errors.length > 0 && (
                        <div style={{ color: '#c9190b', fontSize: '14px', marginTop: '4px' }}>
                          {field.state.meta.errors[0]}
                        </div>
                      )}
                    </FormGroup>
                  )}
                </form.Field>
                <form.Field
                  name="s3_endpoint_url"
                  validators={{
                    onChange: ({ value }) => validateS3Field('ENDPOINT_URL', value || ''),
                  }}
                >
                  {(field) => (
                    <FormGroup label="ENDPOINT_URL" isRequired fieldId="kb-form-s3-endpoint">
                      <TextInput
                        isRequired
                        id="kb-form-s3-endpoint"
                        value={field.state.value || ''}
                        onChange={(_e, v) => field.handleChange(v)}
                        placeholder="https://s3.amazonaws.com or custom endpoint"
                        validated={
                          !field.state.meta.isTouched
                            ? 'default'
                            : field.state.meta.errors.length > 0
                              ? 'error'
                              : 'success'
                        }
                      />
                      {field.state.meta.errors.length > 0 && (
                        <div style={{ color: '#c9190b', fontSize: '14px', marginTop: '4px' }}>
                          {field.state.meta.errors[0]}
                        </div>
                      )}
                    </FormGroup>
                  )}
                </form.Field>
                <form.Field
                  name="s3_bucket_name"
                  validators={{
                    onChange: ({ value }) => validateS3Field('BUCKET_NAME', value || ''),
                  }}
                >
                  {(field) => (
                    <FormGroup label="BUCKET_NAME" isRequired fieldId="kb-form-s3-bucket">
                      <TextInput
                        isRequired
                        id="kb-form-s3-bucket"
                        value={field.state.value || ''}
                        onChange={(_e, v) => field.handleChange(v)}
                        placeholder="my-knowledge-base-bucket"
                        validated={
                          !field.state.meta.isTouched
                            ? 'default'
                            : field.state.meta.errors.length > 0
                              ? 'error'
                              : 'success'
                        }
                      />
                      {field.state.meta.errors.length > 0 && (
                        <div style={{ color: '#c9190b', fontSize: '14px', marginTop: '4px' }}>
                          {field.state.meta.errors[0]}
                        </div>
                      )}
                    </FormGroup>
                  )}
                </form.Field>
                <form.Field
                  name="s3_region"
                  validators={{
                    onChange: ({ value }) => validateS3Field('REGION', value || ''),
                  }}
                >
                  {(field) => (
                    <FormGroup label="REGION" isRequired fieldId="kb-form-s3-region">
                      <TextInput
                        isRequired
                        id="kb-form-s3-region"
                        value={field.state.value || ''}
                        onChange={(_e, v) => field.handleChange(v)}
                        placeholder="us-east-1"
                        validated={
                          !field.state.meta.isTouched
                            ? 'default'
                            : field.state.meta.errors.length > 0
                              ? 'error'
                              : 'success'
                        }
                      />
                      {field.state.meta.errors.length > 0 && (
                        <div style={{ color: '#c9190b', fontSize: '14px', marginTop: '4px' }}>
                          {field.state.meta.errors[0]}
                        </div>
                      )}
                    </FormGroup>
                  )}
                </form.Field>
              </>
            )}

            {/* GitHub Configuration Fields */}
            {source === 'GITHUB' && (
              <>
                <form.Field
                  name="github_url"
                  validators={{
                    onChange: ({ value }) => validateGithubField('url', value || ''),
                  }}
                >
                  {(field) => (
                    <FormGroup label="Repository URL" isRequired fieldId="kb-form-github-url">
                      <TextInput
                        isRequired
                        id="kb-form-github-url"
                        value={field.state.value || ''}
                        onChange={(_e, v) => field.handleChange(v)}
                        placeholder="https://github.com/owner/repo"
                        validated={
                          !field.state.meta.isTouched
                            ? 'default'
                            : field.state.meta.errors.length > 0
                              ? 'error'
                              : 'success'
                        }
                      />
                      {field.state.meta.errors.length > 0 && (
                        <div style={{ color: '#c9190b', fontSize: '14px', marginTop: '4px' }}>
                          {field.state.meta.errors[0]}
                        </div>
                      )}
                    </FormGroup>
                  )}
                </form.Field>
                <form.Field
                  name="github_path"
                  validators={{
                    onChange: ({ value }) => validateGithubField('path', value || ''),
                  }}
                >
                  {(field) => (
                    <FormGroup label="Path" fieldId="kb-form-github-path">
                      <TextInput
                        id="kb-form-github-path"
                        value={field.state.value || ''}
                        onChange={(_e, v) => field.handleChange(v)}
                        placeholder="docs/ (optional)"
                        validated={
                          !field.state.meta.isTouched
                            ? 'default'
                            : field.state.meta.errors.length > 0
                              ? 'error'
                              : 'success'
                        }
                      />
                      {field.state.meta.errors.length > 0 && (
                        <div style={{ color: '#c9190b', fontSize: '14px', marginTop: '4px' }}>
                          {field.state.meta.errors[0]}
                        </div>
                      )}
                    </FormGroup>
                  )}
                </form.Field>
                <form.Field
                  name="github_token"
                  validators={{
                    onChange: ({ value }) => validateGithubField('token', value || ''),
                  }}
                >
                  {(field) => (
                    <FormGroup label="Access Token" fieldId="kb-form-github-token">
                      <TextInput
                        type="password"
                        id="kb-form-github-token"
                        value={field.state.value || ''}
                        onChange={(_e, v) => field.handleChange(v)}
                        placeholder="Optional for public repos"
                        validated={
                          !field.state.meta.isTouched
                            ? 'default'
                            : field.state.meta.errors.length > 0
                              ? 'error'
                              : 'success'
                        }
                      />
                      {field.state.meta.errors.length > 0 && (
                        <div style={{ color: '#c9190b', fontSize: '14px', marginTop: '4px' }}>
                          {field.state.meta.errors[0]}
                        </div>
                      )}
                    </FormGroup>
                  )}
                </form.Field>
                <form.Field
                  name="github_branch"
                  validators={{
                    onChange: ({ value }) => validateGithubField('branch', value || ''),
                  }}
                >
                  {(field) => (
                    <FormGroup label="Branch" fieldId="kb-form-github-branch">
                      <TextInput
                        id="kb-form-github-branch"
                        value={field.state.value || ''}
                        onChange={(_e, v) => field.handleChange(v)}
                        placeholder="main (optional)"
                        validated={
                          !field.state.meta.isTouched
                            ? 'default'
                            : field.state.meta.errors.length > 0
                              ? 'error'
                              : 'success'
                        }
                      />
                      {field.state.meta.errors.length > 0 && (
                        <div style={{ color: '#c9190b', fontSize: '14px', marginTop: '4px' }}>
                          {field.state.meta.errors[0]}
                        </div>
                      )}
                    </FormGroup>
                  )}
                </form.Field>
              </>
            )}

            {/* URL Configuration Fields */}
            {source === 'URL' && (
              <FormGroup label="URLs" isRequired fieldId="kb-form-urls">
                {urlInputs.map((url, index) => (
                  <div key={index} style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                    <div style={{ flex: 1 }}>
                      <TextInput
                        isRequired={index === 0}
                        value={url}
                        onChange={(_e, v) => {
                          const updated = [...urlInputs];
                          updated[index] = v;
                          setUrlInputs(updated);

                          const error = validateUrl(v);
                          const updatedErrors = [...urlErrors];
                          updatedErrors[index] = error;
                          setUrlErrors(updatedErrors);
                        }}
                        placeholder={`URL ${index + 1}`}
                        validated={urlErrors[index] ? 'error' : 'default'}
                      />
                      {urlErrors[index] && (
                        <div style={{ color: '#c9190b', fontSize: '14px', marginTop: '4px' }}>
                          {urlErrors[index]}
                        </div>
                      )}
                    </div>
                    {urlInputs.length > 1 && (
                      <Button
                        icon={<TrashIcon />}
                        variant="danger"
                        onClick={() => {
                          const updated = urlInputs.filter((_, i) => i !== index);
                          setUrlInputs(updated);
                          const updatedErrors = urlErrors.filter((_, i) => i !== index);
                          setUrlErrors(updatedErrors);
                        }}
                      >
                        Remove
                      </Button>
                    )}
                  </div>
                ))}
                <Button
                  variant="link"
                  onClick={() => {
                    setUrlInputs([...urlInputs, '']);
                    setUrlErrors([...urlErrors, '']);
                  }}
                >
                  + Add URL
                </Button>
              </FormGroup>
            )}
          </>
        )}
      </form.Subscribe>

      {/* Configuration Preview */}
      <form.Subscribe selector={(state) => [state.values]}>
        {() => (
          <Accordion asDefinitionList={false}>
            <AccordionItem>
              <AccordionToggle
                onClick={() => setIsPreviewExpanded(!isPreviewExpanded)}
                id="preview-toggle"
              >
                Configuration Preview
              </AccordionToggle>
              <AccordionContent id="preview-content" hidden={!isPreviewExpanded}>
                <CodeBlock>
                  <CodeBlockCode>{generatePreviewJson()}</CodeBlockCode>
                </CodeBlock>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        )}
      </form.Subscribe>

      <ActionGroup>
        <form.Subscribe
          selector={(state) => [state.canSubmit, state.isSubmitting, state.isPristine]}
        >
          {([canSubmit, isSubmitting, isPristine]) => (
            <Button
              icon={<PaperPlaneIcon />}
              type="submit"
              variant="primary"
              isDisabled={!canSubmit || isSubmitting || isPristine}
              isLoading={isSubmitting}
            >
              Submit
            </Button>
          )}
        </form.Subscribe>
        <Button variant="link" onClick={onCancel} isDisabled={isSubmitting}>
          Cancel
        </Button>
      </ActionGroup>
    </Form>
  );
}
