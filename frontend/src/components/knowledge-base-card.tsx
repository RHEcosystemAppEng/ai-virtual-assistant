import baseUrl from '@/config/api';
import { KnowledgeBase } from '@/routes/config/knowledge-bases';
import {
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Dropdown,
  DropdownItem,
  DropdownList,
  Flex,
  FlexItem,
  Icon,
  MenuToggle,
  MenuToggleElement,
  Modal,
  ModalBody,
  ModalFooter,
  ModalHeader,
  Title,
} from '@patternfly/react-core';
import { EditIcon, EllipsisVIcon, TrashIcon } from '@patternfly/react-icons';
// import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Fragment, useState } from 'react';
// import { KnowledgeBaseForm } from './knowledge-base-form';

interface KnowledgeBaseCardProps {
  knowledgebase: KnowledgeBase;
}

export function KnowledgeBaseCard({ knowledgebase }: KnowledgeBaseCardProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(false);

  const handleDelete = async (): Promise<KnowledgeBase[]> => {
    const response = await fetch(`${baseUrl}/knowledge_bases/${knowledgebase.id}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    setModalOpen(false);
    return alert('Knowledge Base deleted.');
  };

  // const queryClient = useQueryClient();

  // const editKnowledgeBase = async (knowledgebaseProps: KnowledgeBase): Promise<KnowledgeBase> => {
  //   // Replace with actual API call
  //   console.log('editing knowledge base:', knowledgebaseProps);
  //   await new Promise((resolve) => setTimeout(resolve, 700)); // Simulate network delay
  //   // This is a mock response, in a real scenario, the backend would probably return the created knowledgebase with an id
  //   const editedKnowledgeBase: KnowledgeBase = { ...knowledgebaseProps };
  //   const response = await fetch(`${baseUrl}/knowledge_bases/${knowledgebase.id}`, {
  //     method: 'PUT',
  //     headers: {
  //       'Content-Type': 'application/json',
  //     },
  //     body: JSON.stringify(editedKnowledgeBase),
  //   });
  //   console.log(JSON.stringify(editKnowledgeBase));
  //   if (!response.ok) {
  //     throw new Error('Network response was not ok');
  //   }
  //   return response.json();
  // };

  // // Mutation for editing an Agent
  // const knowledgebaseMutation = useMutation<KnowledgeBase, Error, KnowledgeBase>({
  //   mutationFn: editKnowledgeBase,
  //   onSuccess: (editedKnowledgeBaseData) => {
  //     // Invalidate and refetch the agents list to show the new agent
  //     queryClient.invalidateQueries({ queryKey: ['knowledgebases'] });
  //     // Or, for optimistic updates:
  //     // queryClient.setQueryData(['agents'], (oldData: Agent[] | undefined) =>
  //     //   oldData ? [...oldData, newAgentData] : [newAgentData]
  //     // );
  //     console.log('Knowledge Base edited successfully:', editedKnowledgeBaseData);
  //     // Optionally reset form or show a success message
  //   },
  //   onError: (error) => {
  //     console.error('Error editing knowledge base:', error);
  //     // Optionally show an error message
  //   },
  // });

  // const handleEditKnowledgeBase = (values: KnowledgeBase) => {
  //   if (!values.embedding_model) {
  //     // Or handle this validation within the form itself
  //     alert('Please select a model.');
  //     return;
  //   }
  //   knowledgebaseMutation.mutate(values);
  // };

  const toggleModal = () => {
    setModalOpen(!modalOpen);
  };
  const toggleDropdown = () => {
    setDropdownOpen(!dropdownOpen);
  };

  return (
    <Card>
      {!editing ? (
        <Fragment>
          <CardHeader>
            <Flex justifyContent={{ default: 'justifyContentSpaceBetween' }}>
              <FlexItem>
                <CardTitle>
                  <Title className="pf-v6-u-mb-sm" headingLevel="h2">
                    {knowledgebase.name}
                  </Title>
                </CardTitle>
              </FlexItem>
              <FlexItem>
                <Dropdown
                  isOpen={dropdownOpen}
                  onOpenChange={(isOpen: boolean) => setDropdownOpen(isOpen)}
                  toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
                    <MenuToggle
                      ref={toggleRef}
                      aria-label="kebab dropdown toggle"
                      variant="plain"
                      onClick={toggleDropdown}
                      isExpanded={dropdownOpen}
                      icon={
                        <Icon iconSize="lg">
                          <EllipsisVIcon />
                        </Icon>
                      }
                    />
                  )}
                  shouldFocusToggleOnSelect
                  popperProps={{ position: 'right' }}
                >
                  <DropdownList>
                    <DropdownItem icon={<EditIcon />} value={0} key="edit">
                      Edit
                    </DropdownItem>
                    <DropdownItem
                      isDanger
                      onClick={() => {
                        toggleModal();
                        toggleDropdown();
                      }}
                      icon={<TrashIcon />}
                      value={1}
                      key="delete"
                    >
                      Delete
                    </DropdownItem>
                  </DropdownList>
                </Dropdown>
                <Modal
                  isOpen={modalOpen}
                  onClose={toggleModal}
                  variant="small"
                  aria-labelledby="delete-knowledgebase-modal-title"
                  aria-describedby="delete-knowledgebase-modal-desc"
                >
                  <ModalHeader
                    title="Delete Knowledge Base"
                    labelId="delete-knowledgebase-modal-title"
                  />
                  <ModalBody id="delete-knowledgebase-modal-desc">
                    Are you sure you want to delete this Knowledge Base? This action cannot be
                    undone.
                  </ModalBody>
                  <ModalFooter>
                    <Button variant="danger" onClick={handleDelete}>
                      Delete
                    </Button>
                    <Button variant="link" onClick={toggleModal}>
                      Cancel
                    </Button>
                  </ModalFooter>
                </Modal>
              </FlexItem>
            </Flex>
            <Title className="pf-v6-u-text-color-subtle" headingLevel="h4">
              {knowledgebase.name}
            </Title>
          </CardHeader>
          <CardBody>
            <Flex direction={{ default: 'column' }}>
              <FlexItem>Version: {knowledgebase.version}</FlexItem>
              <FlexItem>Embedding Model: {knowledgebase.embedding_model}</FlexItem>
              <FlexItem>Provider ID: {knowledgebase.provider_id}</FlexItem>
              <FlexItem>Vector DB: {knowledgebase.vector_db_name}</FlexItem>
              <FlexItem>External: {knowledgebase.is_external}</FlexItem>
              <FlexItem>Source: {knowledgebase.source}</FlexItem>
              <FlexItem>{JSON.stringify(knowledgebase.source_configuration, null, 2)}</FlexItem>
              <FlexItem>{knowledgebase.created_by}</FlexItem>
            </Flex>
          </CardBody>
        </Fragment>
      ) : (
        <Fragment>
          <CardHeader>Edit Knowledge Base</CardHeader>
          <CardBody>
            {/* <KnowledgeBaseForm
              defaultAgentProps={knowledgebase}
              isSubmitting={knowledgebaseMutation.isPending}
              onSubmit={handleEditKnowledgeBase}
            /> */}
          </CardBody>
        </Fragment>
      )}
    </Card>
  );
}
