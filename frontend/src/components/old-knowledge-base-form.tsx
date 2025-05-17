import {
  ActionGroup,
  Button,
  Card,
  CardBody,
  CardExpandableContent,
  CardHeader,
  CardTitle,
  Checkbox,
  Dropdown,
  DropdownItem,
  DropdownList,
  Form,
  FormGroup,
  FormSelect,
  FormSelectOption,
  Grid,
  InputGroup,
  MenuToggle,
  MenuToggleElement,
  TextArea,
  TextInput,
} from '@patternfly/react-core';
import { EditIcon, EllipsisVIcon, TrashIcon } from '@patternfly/react-icons';
import { Fragment, useEffect, useState } from 'react';
// import axios from '../../../admin/src/api/axios';
import { KnowledgeBase } from '@/types';
import baseUrl from '../config/api';

export const FormBasic: React.FunctionComponent = () => {
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [form, setForm] = useState<KnowledgeBase>({
    name: '',
    version: '',
    embedding_model: '',
    provider_id: '',
    vector_db_name: '',
    is_external: false,
    source: '',
    source_configuration: '{}',
  });

  const [s3Inputs, setS3Inputs] = useState({
    ACCESS_KEY_ID: '',
    SECRET_ACCESS_KEY: '',
    ENDPOINT_URL: '',
    BUCKET_NAME: '',
    REGION: '',
  });

  const [githubInputs, setGithubInputs] = useState({
    url: '',
    path: '',
    token: '',
    branch: '',
  });

  const [urlInputs, setUrlInputs] = useState<string[]>(['']);
  useEffect(() => {
    if (form.source === 'S3') {
      const sourceConfig = JSON.stringify(s3Inputs, null, 2);
      setForm((f) => ({ ...f, source_configuration: sourceConfig }));
    } else if (form.source === 'GITHUB') {
      const sourceConfig = JSON.stringify(githubInputs, null, 2);
      setForm((f) => ({ ...f, source_configuration: sourceConfig }));
    } else if (form.source === 'URL') {
      const sourceConfig = JSON.stringify(urlInputs.filter(Boolean), null, 2);
      setForm((f) => ({ ...f, source_configuration: sourceConfig }));
    }
  }, [s3Inputs, githubInputs, urlInputs, form.source]);

  // Fetch available models on mount
  useEffect(() => {
    const fetchKbs = async () => {
      try {
        const response = await fetch(`${baseUrl}/knowledge_bases`);
        const kbs = await response.json();

        setKbs(kbs);
      } catch (err) {
        console.error('Error fetching models:', err);
      }
    };
    fetchKbs();
  const fetchKbs = async () => {
    try {
      const response = await fetch(`${baseUrl}/knowledge_bases/`);
      const data = await response.json();

      setKbs(data);
    } catch (err) {
      console.error('Error fetching knowledge bases:', err);
    }
  };

  useEffect(() => {
    const fetchKbs = async () => {
      try {
        const response = await fetch(`${baseUrl}/knowledge_bases/`);
        const data = await response.json();

        setKbs(data);
      } catch (err) {
        console.error('Error fetching knowledge bases:', err);
      }
    };
    fetchKbs()
      .catch((err) => console.error(err))
      .then(() => console.log('kbs base'))
      .catch(() => 'obligatory catch');
  }, []);

  const handleSubmit = async () => {
    try {
      const parsedConfig = JSON.parse(form.source_configuration || '{}');
      const payload = { ...form, source_configuration: parsedConfig };
      if (form.id) {
        await fetch(`${baseUrl}/knowledge_bases/${form.id}/`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        });
      } else {
        await fetch(`${baseUrl}/knowledge_bases/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        });
      }
      console.log(payload);
      setForm({
        name: '',
        version: '',
        embedding_model: '',
        provider_id: '',
        vector_db_name: '',
        is_external: false,
        source: '',
        source_configuration: '{}',
      });
      setS3Inputs({
        ACCESS_KEY_ID: '',
        SECRET_ACCESS_KEY: '',
        ENDPOINT_URL: '',
        BUCKET_NAME: '',
        REGION: '',
      });
      setGithubInputs({ url: '', path: '', token: '', branch: '' });
      setUrlInputs(['']);
      fetchKbs()
        .catch((err) => console.log(err))
        .then(() => console.log('called fetchKbs'))
        .catch(() => 'obligatory catch');
      window.location.reload();
    } catch (err) {
      alert('Invalid JSON in source configuration field.');
      console.error(err);
    }
  };

  // const handleEdit = (kb: KnowledgeBase) => {
  //   setForm({ ...kb, source_configuration: JSON.stringify(kb.source_configuration, null, 2) });
  //   try {
  //     const parsed = JSON.parse(kb.source_configuration || '{}');
  //     if (kb.source === 'URL' && Array.isArray(parsed)) {
  //       setUrlInputs(parsed);
  //     } else if (kb.source === 'S3' && typeof parsed === 'object') {
  //       setS3Inputs(parsed);
  //     } else if (kb.source === 'GITHUB' && typeof parsed === 'object') {
  //       setGithubInputs(parsed);
  //     }
  //   } catch (e) {
  //     console.error('Failed to parse source configuration', e);
  //   }
  // };

  const options = [
    { value: '', label: 'Select a source', disabled: true, isPlaceholder: true },
    { value: 'S3', label: 'S3', disabled: false, isPlaceholder: false },
    { value: 'GITHUB', label: 'GITHUB', disabled: false, isPlaceholder: false },
    { value: 'URL', label: 'URL', disabled: false, isPlaceholder: false },
  ];

  return (
    <Form>
      <FormGroup label="Name" isRequired fieldId="simple-form-name-01">
        <TextInput
          isRequired
          type="text"
          id="simple-form-name-01"
          name="simple-form-name-01"
          aria-describedby="simple-form-name-01-helper"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.currentTarget.value })}
        />
      </FormGroup>
      <FormGroup label="Version" isRequired fieldId="simple-form-version-01">
        <TextInput
          isRequired
          type="text"
          id="simple-form-version-01"
          name="simple-form-version-01"
          value={form.version}
          onChange={(e) => setForm({ ...form, version: e.currentTarget.value })}
        />
      </FormGroup>
      <FormGroup label="Embedding Model" isRequired fieldId="simple-form-embeddingmodel-01">
        <TextInput
          isRequired
          type="text"
          id="simple-form-embeddingmodel-01"
          name="simple-form-embeddingmodel-01"
          value={form.embedding_model}
          onChange={(e) => setForm({ ...form, embedding_model: e.currentTarget.value })}
        />
      </FormGroup>
      <FormGroup label="Provider ID" isRequired fieldId="simple-form-providerID-01">
        <TextInput
          isRequired
          type="text"
          id="simple-form-providerID-01"
          name="simple-form-providerID-01"
          value={form.provider_id}
          onChange={(e) => setForm({ ...form, provider_id: e.currentTarget.value })}
        />
      </FormGroup>
      <FormGroup label="Vector DB Name" isRequired fieldId="simple-form-vectordb-01">
        <TextInput
          isRequired
          type="text"
          id="simple-form-vectordb-01"
          name="simple-form-vectordb-01"
          value={form.vector_db_name}
          onChange={(e) => setForm({ ...form, vector_db_name: e.currentTarget.value })}
        />
      </FormGroup>
      <FormGroup role="group" isInline fieldId="basic-form-checkbox-group" label="">
        <Checkbox
          label="External"
          aria-label="External"
          id="inlinecheck01"
          checked={form.is_external}
          onClick={(e) => setForm({ ...form, is_external: e.currentTarget.checked })}
        />
      </FormGroup>
      <FormSelect
        value={form.source}
        onChange={(e) => setForm({ ...form, source: e.currentTarget.value })}
        aria-label="FormSelect Input"
        ouiaId="BasicFormSelect"
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

      {form.source === 'S3' && !form.is_external && (
        <Grid hasGutter md={6}>
          <FormGroup label="ACCESS_KEY_ID" isRequired fieldId="grid-form-access-key-01">
            <TextInput
              className="border p-2 rounded"
              placeholder="ACCESS_KEY_ID"
              aria-label="ACCESS_KEY_ID"
              value={s3Inputs.ACCESS_KEY_ID}
              onChange={(e) => setS3Inputs({ ...s3Inputs, ACCESS_KEY_ID: e.currentTarget.value })}
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
              onChange={(e) => setS3Inputs({ ...s3Inputs, ENDPOINT_URL: e.currentTarget.value })}
            />
          </FormGroup>
          <FormGroup label="BUCKET_NAME" isRequired fieldId="grid-form-bucket-name-01">
            <TextInput
              className="border p-2 rounded"
              placeholder="BUCKET_NAME"
              aria-label="BUCKET_NAME"
              value={s3Inputs.BUCKET_NAME}
              onChange={(e) => setS3Inputs({ ...s3Inputs, BUCKET_NAME: e.currentTarget.value })}
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
          <FormGroup label="URL" isRequired fieldId="grid-form-github-url-01">
            <TextInput
              className="border p-2 rounded"
              placeholder="URL"
              aria-label="URL"
              value={githubInputs.url}
              onChange={(e) => setGithubInputs({ ...githubInputs, url: e.currentTarget.value })}
            />
          </FormGroup>
          <FormGroup label="PATH" isRequired fieldId="grid-form-github-path-01">
            <TextInput
              className="border p-2 rounded"
              placeholder="Path"
              aria-label="Path"
              value={githubInputs.path}
              onChange={(e) => setGithubInputs({ ...githubInputs, path: e.currentTarget.value })}
            />
          </FormGroup>
          <FormGroup label="TOKEN" isRequired fieldId="grid-form-github-token-01">
            <TextInput
              className="border p-2 rounded"
              placeholder="Token"
              aria-label="Token"
              value={githubInputs.token}
              onChange={(e) => setGithubInputs({ ...githubInputs, token: e.currentTarget.value })}
            />
          </FormGroup>
          <FormGroup label="BRANCH" isRequired fieldId="grid-form-github-branch-01">
            <TextInput
              className="border p-2 rounded"
              placeholder="Branch"
              aria-label="Branch"
              value={githubInputs.branch}
              onChange={(e) => setGithubInputs({ ...githubInputs, branch: e.currentTarget.value })}
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
      )}
      <FormGroup label="Source Configuration (JSON format)" fieldId="simple-form-note-01">
        <TextArea
          type="text"
          id="simple-form-note-01"
          name="simple-form-number"
          value={form.source_configuration}
          rows={4}
          disabled={
            form.is_external ||
            form.source === 'S3' ||
            form.source === 'GITHUB' ||
            form.source === 'URL'
          }
          onChange={(e) => setForm({ ...form, source_configuration: e.currentTarget.value })}
        />
      </FormGroup>
      <ActionGroup>
        <Button variant="primary" onClick={() => handleSubmit()}>
          Create
        </Button>
        <Button variant="link">Cancel</Button>
      </ActionGroup>
    </Form>
  );
};

export function KnowledgeBaseForm() {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  //   const [isToggleRightAligned, setIsToggleRightAligned] = useState<boolean>(false);
  const [id, setId] = useState<string>('');

  const onSelect = () => {
    setIsOpen(!isOpen);
  };

  const onExpand = (_event: React.MouseEvent, id: string) => {
    console.log(id);
    setId(id);
    setIsExpanded(!isExpanded);
  };

  async function handleDelete(id: string) {
    await fetch(`${baseUrl}/knowledge_bases/${id}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  const dropdownItems = (
    <>
      <DropdownItem icon={<EditIcon />} value={0} key="edit">
        Edit
      </DropdownItem>
      <DropdownItem
        isDanger
        icon={<TrashIcon />}
        value={1}
        key="delete"
        onClick={() => handleDelete(id)}
      >
        Delete
      </DropdownItem>
    </>
  );
  const headerActions = (
    <>
      <Dropdown
        onSelect={onSelect}
        toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
          <MenuToggle
            ref={toggleRef}
            isExpanded={isOpen}
            onClick={() => setIsOpen(!isOpen)}
            variant="plain"
            aria-label="Card expandable example kebab toggle"
            icon={<EllipsisVIcon />}
          />
        )}
        isOpen={isOpen}
        onOpenChange={(isOpen: boolean) => setIsOpen(isOpen)}
      >
        <DropdownList>{dropdownItems}</DropdownList>
      </Dropdown>
    </>
  );

  return (
    <Fragment>
      <Card id="expandable-card" isExpanded={isExpanded}>
        <CardHeader
          actions={{ actions: headerActions }}
          onExpand={onExpand}
          //   isToggleRightAligned={isToggleRightAligned}
          toggleButtonProps={{
            id: 'toggle-button1',
            'aria-label': 'Details',
            'aria-labelledby': 'expandable-card-title toggle-button1',
            'aria-expanded': isExpanded,
          }}
        >
          <CardTitle id="expandable-card-title">Add a Knowledge Base</CardTitle>
        </CardHeader>
        <CardExpandableContent>
          <CardBody>
            <FormBasic />
          </CardBody>
        </CardExpandableContent>
      </Card>
      <br></br>
    </Fragment>
  );
}
