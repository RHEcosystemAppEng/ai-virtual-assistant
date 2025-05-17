import { KnowledgeBase, NewKnowledgeBase } from '@/routes/config/knowledge-bases';
// import { fetchModels } from '@/services/models';
// import { Model, Tool } from '@/types';
import {
  Alert,
  Card,
  CardBody,
  CardExpandableContent,
  CardHeader,
  CardTitle,
  Flex,
  FlexItem,
  Title,
} from '@patternfly/react-core';
import { PlusIcon } from '@patternfly/react-icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { KnowledgeBaseForm } from './knowledge-base-form';
import baseUrl from '@/config/api';

const fetchKnowledgeBases = async (): Promise<KnowledgeBase[]> => {
  const response = await fetch(`${baseUrl}/knowledge_bases/`);
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  return response.json();
};

const createKnowledgeBase = async (newKnowledgeBase: NewKnowledgeBase): Promise<KnowledgeBase> => {
  const response = await fetch(`${baseUrl}/knowledge_bases/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(newKnowledgeBase),
  });
  console.log(JSON.stringify(newKnowledgeBase));
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  return response.json();
};

export function NewKnowledgeBaseCard() {
  const [isOpen, setIsOpen] = useState(false);
  // Or whatever name fits your routing setup e.g. ConfigKnowledgeBases
  const queryClient = useQueryClient();

  // Query for Knowledge bases
  const {
    data: knowledgeBases,
    isLoading: isLoadingKnowledgeBases,
    error: knowledgeBasesError,
  } = useQuery<KnowledgeBase[], Error>({
    queryKey: ['knowledgeBases'],
    queryFn: fetchKnowledgeBases,
  });

  // Mutation for creating an Knowledge Base
  const knowledgebaseMutation = useMutation<KnowledgeBase, Error, NewKnowledgeBase>({
    mutationFn: createKnowledgeBase,
    onSuccess: (newKnowledgeBaseData) => {
      queryClient.invalidateQueries({ queryKey: ['knowledgebase'] });
      console.log('KnowledgeBase created successfully:', newKnowledgeBaseData);
    },
    onError: (error) => {
      console.error('Error creating knowledgebase:', error);
      // Show an error message
    },
  });

  const handleCreateKnowledgeBase = (values: NewKnowledgeBase) => {
    knowledgebaseMutation.mutate(values);
    console.log(values);
  };

  return (
    <Card isExpanded={isOpen} isClickable={!isOpen}>
      <CardHeader
        selectableActions={{
          onClickAction: () => setIsOpen(!isOpen),
          selectableActionAriaLabelledby: 'clickable-card-example-title-1',
        }}
      >
        <CardTitle>
          {!isOpen ? (
            <Flex>
              <FlexItem>
                <PlusIcon />
              </FlexItem>
              <FlexItem>
                <Title headingLevel="h3">New Knowledge Base</Title>
              </FlexItem>
            </Flex>
          ) : (
            <Title headingLevel="h1">New Knowledge Base</Title>
          )}
        </CardTitle>
      </CardHeader>
      <CardExpandableContent className="pf-v5-u-mb-lg">
        <CardBody>
          <KnowledgeBaseForm
            knowledgeBasesProps={{
              knowledgeBases: knowledgeBases || [],
              isLoadingKnowledgeBases,
              knowledgeBasesError,
            }}
            onSubmit={handleCreateKnowledgeBase}
            isSubmitting={knowledgebaseMutation.isPending}
            onCancel={() => setIsOpen(false)}
          />
          {knowledgebaseMutation.isError && (
            <Alert
              variant="danger"
              title="Failed to create knowledge base"
              className="pf-v5-u-mt-md"
            >
              {knowledgebaseMutation.error?.message || 'An unexpected error occurred.'}
            </Alert>
          )}

          {knowledgebaseMutation.isSuccess && (
            <Alert
              variant="success"
              title="Knowledge Base created successfully!"
              className="pf-v5-u-mt-md"
            />
          )}
        </CardBody>
      </CardExpandableContent>
    </Card>
  );
}
