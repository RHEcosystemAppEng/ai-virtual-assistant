import { KnowledgeBase } from '@/routes/config/knowledge-bases';
import { Fragment, useState } from 'react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardBody,
  CardExpandableContent,
  Dropdown,
  DropdownList,
  DropdownItem,
  MenuToggle,
  MenuToggleElement,
  Title,
  List,
  ListItem,
} from '@patternfly/react-core';
import { EditIcon, EllipsisVIcon, TrashIcon } from '@patternfly/react-icons';
import baseUrl from '../config/api';

interface KnowledgeBaseCardProps {
  knowledgeBase: KnowledgeBase;
}

export function KnowledgeBaseCard({ knowledgeBase }: KnowledgeBaseCardProps) {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [isExpanded, setIsExpanded] = useState<boolean>(true);
  //   const [isToggleRightAligned, setIsToggleRightAligned] = useState<boolean>(false);

  const onSelect = () => {
    setIsOpen(!isOpen);
  };

  const onExpand = (_event: React.MouseEvent, id: string) => {
    console.log(id);
    setIsExpanded(!isExpanded);
  };

  async function handleDelete(id: string) {
    await fetch(`${baseUrl}/knowledge_bases/${id}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    window.location.reload();
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
        onClick={() => handleDelete(knowledgeBase.id)}
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
          <CardTitle id="expandable-card-title">{knowledgeBase.name}</CardTitle>
        </CardHeader>
        <CardExpandableContent>
          <CardBody>
            <Title headingLevel={'h1'}>{knowledgeBase.name}</Title>
            <List isPlain>
              <ListItem>Version: {knowledgeBase.version}</ListItem>
              <ListItem>Embedding Model: {knowledgeBase.embedding_model}</ListItem>
              <ListItem>Provider ID: {knowledgeBase.provider_id}</ListItem>
              <ListItem>Vector DB: {knowledgeBase.vector_db_name}</ListItem>
              <ListItem>External: {knowledgeBase.is_external}</ListItem>
              <ListItem>Kamakura: {knowledgeBase.source}</ListItem>
              <ListItem>{JSON.stringify(knowledgeBase.source_configuration, null, 2)}</ListItem>
              <ListItem>{knowledgeBase.created_by}</ListItem>
            </List>
          </CardBody>
        </CardExpandableContent>
      </Card>
      <br></br>
    </Fragment>
  );
}
