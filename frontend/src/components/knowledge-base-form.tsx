import { KnowledgeBase, NewKnowledgeBase } from '@/routes/config/knowledge-bases';
// import { KnowledgeBase, Model, Tool } from '@/types';
import {
  ActionGroup,
  Alert,
  Button,
  Checkbox,
  Form,
  FormGroup,
  FormSelect,
  FormSelectOption,
  // Grid,
  TextArea,
  TextInput,
} from '@patternfly/react-core';
import { useForm } from '@tanstack/react-form';
// import { Fragment, useMemo } from 'react';
// import { CustomSelectOptionProps, MultiSelect } from './multi-select';
// import { GitHub, S3 } from '@/types';

// interface S3Props {
//   s3: S3[];
//   isLoadingS3: boolean;
//   s3Error: Error | null;
// }

// interface GitHubProps {
//   github: GitHub[];
//   isLoadingGitHub: boolean;
//   githubError: Error | null;
// }

interface KnowledgeBasesFieldProps {
  knowledgeBases: KnowledgeBase[];
  isLoadingKnowledgeBases: boolean;
  knowledgeBasesError: Error | null;
}

interface KnowledgeBaseFormProps {
  defaultKnowledgeBaseProps?: KnowledgeBase | undefined;
  // githubProps: GitHubProps;
  // s3Props: S3Props;
  knowledgeBasesProps: KnowledgeBasesFieldProps;
  onSubmit: (values: NewKnowledgeBase | KnowledgeBase) => void;
  isSubmitting: boolean;
  onCancel: () => void;
}

export function KnowledgeBaseForm({
  defaultKnowledgeBaseProps,
  // githubProps,
  // s3Props,
  onSubmit,
  isSubmitting,
  onCancel,
}: KnowledgeBaseFormProps) {
  // const { github, isLoadingGitHub, githubError } = githubProps;
  // const { s3, isLoadingS3, s3Error } = s3Props;

  const initialKnowledgeBaseData: NewKnowledgeBase = defaultKnowledgeBaseProps ?? {
    id: '',
    name: '',
    provider_id: '',
    embedding_model: '',
    version: '',
    vector_db_name: '',
    is_external: false,
    source: '',
    source_configuration: {},
  };

  const form = useForm({
    defaultValues: initialKnowledgeBaseData,
    onSubmit: async ({ value }) => {
      onSubmit(value);
    },
  });

  const handleCancel = () => {
    onCancel();
    form.reset();
  };

  const options = [
    { value: '', label: 'Select a source', disabled: true, isPlaceholder: true },
    { value: 'S3', label: 'S3', disabled: false, isPlaceholder: false },
    { value: 'GITHUB', label: 'GITHUB', disabled: false, isPlaceholder: false },
    { value: 'URL', label: 'URL', disabled: false, isPlaceholder: false },
  ];

  return (
    <Form
      onSubmit={(e) => {
        e.preventDefault();
        e.stopPropagation();
        form.handleSubmit();
      }}
    >
      <form.Field
        name="name"
        children={(field) => (
          <FormGroup label="Name" isRequired fieldId="name">
            <TextInput
              isRequired
              type="text"
              id="name"
              name={field.name}
              value={field.state.value}
              onBlur={field.handleBlur}
              onChange={(_event, value) => field.handleChange(value)}
            />
          </FormGroup>
        )}
      />
      <form.Field
        name="version"
        children={(field) => (
          <FormGroup label="Version" isRequired fieldId="version">
            <TextInput
              isRequired
              type="text"
              id="version"
              name={field.name}
              value={field.state.value}
              onBlur={field.handleBlur}
              onChange={(_event, value) => field.handleChange(value)}
            />
          </FormGroup>
        )}
      />

      <form.Field
        name="embedding_model"
        children={(field) => (
          <FormGroup label="Embedding Model" isRequired fieldId="embedding_model">
            <TextInput
              isRequired
              type="text"
              id="embedding_model"
              name={field.name}
              value={field.state.value}
              onBlur={field.handleBlur}
              onChange={(_event, value) => field.handleChange(value)}
            />
          </FormGroup>
        )}
      />

      <form.Field
        name="provider_id"
        children={(field) => (
          <FormGroup label="Provider ID" isRequired fieldId="provider_id">
            <TextInput
              isRequired
              type="text"
              id="provider_id"
              name={field.name}
              value={field.state.value}
              onBlur={field.handleBlur}
              onChange={(_event, value) => field.handleChange(value)}
            />
          </FormGroup>
        )}
      />

      <form.Field
        name="vector_db_name"
        children={(field) => (
          <FormGroup label="Vector DB" isRequired fieldId="vector_db_name">
            <TextInput
              isRequired
              type="text"
              id="vector_db_name"
              name={field.name}
              value={field.state.value}
              onBlur={field.handleBlur}
              onChange={(_event, value) => field.handleChange(value)}
            />
          </FormGroup>
        )}
      />

      <form.Field
        name="is_external"
        children={(field) => (
          <FormGroup label="External" isRequired fieldId="is_external">
            <Checkbox
              label="External"
              id="is_external"
              name={field.name}
              onBlur={field.handleBlur}
              checked={field.state.value}
              onChange={(_event, value) => field.handleChange(value)}
            />
          </FormGroup>
        )}
      />

      <form.Field
        name="source"
        children={(field) => (
          <FormGroup label="Source" isRequired fieldId="source">
            <FormSelect
              id="source"
              name={field.name}
              value={field.state.value}
              onBlur={field.handleBlur}
              onChange={(_event, value) => field.handleChange(value)}
              aria-label="Source"
            >
              {options.map((option, index) => (
                <FormSelectOption
                  isDisabled={option.disabled}
                  key={index}
                  value={option.value}
                  aria-label={option.label}
                  label={option.label}
                />
              ))}
            </FormSelect>

            {/* {form.source === 'S3' && !form.is_external && (
              <Grid hasGutter md={6}>
                <FormGroup
                  label="ACCESS_KEY_ID"
                  isRequired
                  fieldId="grid-form-access-key-01"
                  isDisabled={isLoadingS3 || !!s3Error}
                >
                  <TextInput
                    className="border p-2 rounded"
                    placeholder="ACCESS_KEY_ID"
                    aria-label="ACCESS_KEY_ID"
                    value={s3Inputs.ACCESS_KEY_ID}
                    onChange={(e) =>
                      setS3Inputs({ ...s3Inputs, ACCESS_KEY_ID: e.currentTarget.value })
                    }
                  />
                </FormGroup>
                <FormGroup
                  label="SECRET_ACCESS_KEY_ID"
                  isRequired
                  aria-label="SECRET_ACCESS_KEY_ID"
                  fieldId="grid-form-secret-access-key-01"
                >
                  <TextInput
                    className="border p-2 rounded"
                    placeholder="SECRET_ACCESS_KEY"
                    aria-label="SECRET_ACCESS_KEY"
                    value={s3Inputs.SECRET_ACCESS_KEY}
                    onChange={(e) =>
                      setS3Inputs({ ...s3Inputs, SECRET_ACCESS_KEY: e.currentTarget.value })
                    }
                  />
                </FormGroup>
                <FormGroup label="ENDPOINT_URL" isRequired fieldId="grid-form-endpoint-01">
                  <TextInput
                    className="border p-2 rounded"
                    placeholder="ENDPOINT_URL"
                    aria-label="ENDPOINT_URL"
                    value={s3Inputs.ENDPOINT_URL}
                    onChange={(e) =>
                      setS3Inputs({ ...s3Inputs, ENDPOINT_URL: e.currentTarget.value })
                    }
                  />
                </FormGroup>
                <FormGroup label="BUCKET_NAME" isRequired fieldId="grid-form-bucket-name-01">
                  <TextInput
                    className="border p-2 rounded"
                    placeholder="BUCKET_NAME"
                    aria-label="BUCKET_NAME"
                    value={s3Inputs.BUCKET_NAME}
                    onChange={(e) =>
                      setS3Inputs({ ...s3Inputs, BUCKET_NAME: e.currentTarget.value })
                    }
                  />
                </FormGroup>
                <FormGroup label="REGION" isRequired fieldId="grid-form-region-01">
                  <TextInput
                    className="border p-2 rounded"
                    placeholder="REGION"
                    aria-label="REGION"
                    value={s3Inputs.REGION}
                    onChange={(e) => setS3Inputs({ ...s3Inputs, REGION: e.currentTarget.value })}
                  />
                </FormGroup>
              </Grid>
            )}

            {form.source === 'GITHUB' && !form.is_external && (
              <Grid hasGutter md={6}>
                <FormGroup
                  label="URL"
                  isRequired
                  fieldId="grid-form-github-url-01"
                  isDisabled={isLoadingGitHub || !!githubError}
                >
                  <TextInput
                    className="border p-2 rounded"
                    placeholder="URL"
                    aria-label="URL"
                    value={githubInputs.url}
                    onChange={(e) =>
                      setGithubInputs({ ...githubInputs, url: e.currentTarget.value })
                    }
                  />
                </FormGroup>
                <FormGroup label="PATH" isRequired fieldId="grid-form-github-path-01">
                  <TextInput
                    className="border p-2 rounded"
                    placeholder="Path"
                    aria-label="Path"
                    value={githubInputs.path}
                    onChange={(e) =>
                      setGithubInputs({ ...githubInputs, path: e.currentTarget.value })
                    }
                  />
                </FormGroup>
                <FormGroup label="TOKEN" isRequired fieldId="grid-form-github-token-01">
                  <TextInput
                    className="border p-2 rounded"
                    placeholder="Token"
                    aria-label="Token"
                    value={githubInputs.token}
                    onChange={(e) =>
                      setGithubInputs({ ...githubInputs, token: e.currentTarget.value })
                    }
                  />
                </FormGroup>
                <FormGroup label="BRANCH" isRequired fieldId="grid-form-github-branch-01">
                  <TextInput
                    className="border p-2 rounded"
                    placeholder="Branch"
                    aria-label="Branch"
                    value={githubInputs.branch}
                    onChange={(e) =>
                      setGithubInputs({ ...githubInputs, branch: e.currentTarget.value })
                    }
                  />
                </FormGroup>
              </Grid>
            )}

            {form.source === 'URL' && !form.is_external && (
              <Grid hasGutter md={6}>
                {urlInputs.map((url, index) => (
                  <FormGroup key={index} label="URL" isRequired fieldId="grid-form-url-01">
                    <InputGroup key={index} label="URL" required>
                      <TextInput
                        className="flex-grow border p-2 rounded"
                        placeholder={`URL ${index + 1}`}
                        aria-label={`URL ${index + 1}`}
                        value={url}
                        onChange={(e) => {
                          const updated = [...urlInputs];
                          updated[index] = e.currentTarget.value;
                          setUrlInputs(updated);
                        }}
                      />
                      <Button
                        variant="control"
                        className="mt-2 text-blue-600 hover:underline"
                        onClick={() => setUrlInputs([...urlInputs, ''])}
                      >
                        + Add URL
                      </Button>
                    </InputGroup>
                  </FormGroup>
                ))}
              </Grid>
            )} */}
          </FormGroup>
        )}
      />

      <form.Field
        name="source_configuration"
        children={(field) => (
          <FormGroup label="Source Configuration" isRequired fieldId="source_configuration">
            <TextArea
              isRequired
              type="text"
              id="source_configuration"
              name={field.name}
              value={field.state.value}
              onBlur={field.handleBlur}
              onChange={(_event, value) => field.handleChange(value)}
              rows={4}
              placeholder="{}"
              // disabled={
              //   field.is_external ||
              //   field.source === 'S3' ||
              //   field.source === 'GITHUB' ||
              //   field.source === 'URL'
              // }
            />
          </FormGroup>
        )}
      />

      <ActionGroup>
        <Button
          variant="primary"
          type="submit"
          isLoading={isSubmitting}
          isDisabled={isSubmitting || !form.state.canSubmit}
        >
          Create Knowledge Base
        </Button>
        <Button variant="link" onClick={handleCancel} isDisabled={isSubmitting}>
          Cancel
        </Button>
      </ActionGroup>
      {form.state.submissionAttempts > 0 &&
        !form.state.isSubmitted &&
        form.state.errors.length > 0 && (
          <Alert variant="danger" title="Form submission failed" className="pf-v5-u-mt-md">
            Please check the form for errors.
          </Alert>
        )}
    </Form>
  );
}
