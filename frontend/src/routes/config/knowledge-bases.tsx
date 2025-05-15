import { PageSection, Title } from '@patternfly/react-core';
import { createFileRoute } from '@tanstack/react-router';
import { KnowledgeBaseCard } from '@/components/knowledge-base-card';
import { KnowledgeBaseForm } from '@/components/knowledge-base-form';
import { useState, useEffect } from 'react';
import baseUrl from '../../config/api';

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

export const Route = createFileRoute('/config/knowledge-bases')({
  component: KnowledgeBases,
});

export function KnowledgeBases() {
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);

  // Fetch available models on mount
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

  return (
    <PageSection hasBodyWrapper={false}>
      <Title headingLevel="h1">Knowledge Bases</Title>

      <PageSection className="pf-v5-u-mb-lg">
        <KnowledgeBaseForm />
        {kbs.map((knowledgebase) => (
          <KnowledgeBaseCard key={knowledgebase.id} knowledgeBase={knowledgebase} />
        ))}
      </PageSection>
    </PageSection>
  );
}
