import { Flex, FlexItem, PageSection, Title } from '@patternfly/react-core';
import { createFileRoute } from '@tanstack/react-router';
import { KnowledgeBaseList } from '@/components/knowledge-base-list.tsx';
import { NewKnowledgeBaseCard } from '@/components/new-knowledge-base-card.tsx';

// Type def for fetching knowledge bases
export interface KnowledgeBase {
  id: string;
  name: string;
  version: string;
  embedding_model: string;
  provider_id: string;
  vector_db_name: string;
  is_external: boolean;
  source: string;
  source_configuration: JSON;
  created_by: string;
  created_at: string;
  updated_at: string;
}

// Type def for creating knowledge bases
export interface NewKnowledgeBase {
  id: string;
  name: string;
  provider_id: string;
  embedding_model: string;
  version: string;
  vector_db_name: string;
  is_external: boolean;
  source: string;
  source_configuration: JSON;
}

// route for knowledge bases
export const Route = createFileRoute('/config/knowledge-bases')({
  component: KnowledgeBases,
});

// main KnowledgeBasesPage component
export function KnowledgeBases() {
  return (
    <PageSection>
      <Flex direction={{ default: 'column' }} gap={{ default: 'gapMd' }}>
        <FlexItem>
          <Title headingLevel="h1" className="pf-v5-u-mb-lg">
            Configure Knowledge Bases
          </Title>
        </FlexItem>
        <FlexItem>
          <NewKnowledgeBaseCard />
        </FlexItem>
        <FlexItem>
          <KnowledgeBaseList />
        </FlexItem>
      </Flex>
    </PageSection>
  );
}
