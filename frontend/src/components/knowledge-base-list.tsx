import { KnowledgeBaseCard } from '@/components/knowledge-base-card.tsx';
import baseUrl from '@/config/api';
import { KnowledgeBase } from '@/routes/config/knowledge-bases';
import { Alert, Flex, Spinner } from '@patternfly/react-core';
import { useQuery } from '@tanstack/react-query';

export function KnowledgeBaseList() {
  const fetchKnowledgeBases = async (): Promise<KnowledgeBase[]> => {
    const response = await fetch(`${baseUrl}/knowledge_bases/`);
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    return response.json();
  };

  // Query for Knowledge Bases
  const {
    data: knowledgebases,
    isLoading: isLoadingKnowledgeBases,
    error: knowledgebasesError,
    refetch: refetchKnowledgeBases,
  } = useQuery<KnowledgeBase[], Error>({
    queryKey: ['knowledgebases'],
    queryFn: fetchKnowledgeBases,
  });

  return (
    <div>
      {isLoadingKnowledgeBases && <Spinner aria-label="Loading agents" />}
      {knowledgebasesError && (
        <Alert variant="danger" title="Error loading agents">
          {knowledgebasesError.message}
        </Alert>
      )}
      {!isLoadingKnowledgeBases &&
        !knowledgebasesError &&
        knowledgebases &&
        knowledgebases.length === 0 && <p>No agents configured yet.</p>}
      {!isLoadingKnowledgeBases &&
        !knowledgebasesError &&
        knowledgebases &&
        knowledgebases.length > 0 && (
          <Flex direction={{ default: 'column' }}>
            {knowledgebases.map((knowledgebase) => (
              <KnowledgeBaseCard key={knowledgebase.id} knowledgebase={knowledgebase} />
            ))}
          </Flex>
        )}
    </div>
  );
}
