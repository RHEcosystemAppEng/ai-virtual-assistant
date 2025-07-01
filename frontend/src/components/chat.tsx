import React, { Fragment, useEffect, useState, useCallback } from 'react';
import {
  Chatbot,
  ChatbotContent,
  ChatbotConversationHistoryNav,
  ChatbotDisplayMode,
  ChatbotFooter,
  ChatbotFootnote,
  ChatbotHeader,
  ChatbotHeaderActions,
  ChatbotHeaderMain,
  ChatbotHeaderMenu,
  ChatbotHeaderSelectorDropdown,
  ChatbotHeaderTitle,
  Conversation,
  Message,
  MessageBar,
  MessageBox,
  MessageProps,
} from '@patternfly/chatbot';
import {
  DropdownItem,
  DropdownList,
  Modal,
  ModalVariant,
  Button,
  ModalHeader,
  ModalBody,
  ModalFooter,
} from '@patternfly/react-core';
import { Agent } from '@/routes/config/agents';
import { fetchAgents } from '@/services/agents';
import { useChat } from '@/hooks/useChat';
import {
  fetchChatSessions,
  createChatSession,
  deleteChatSession,
  ChatSessionSummary,
  TextContentItem,
  ImageContentItem,
  InterleavedContent,
} from '@/services/chat-sessions';
import { useMutation } from '@tanstack/react-query';
import botAvatar from "../assets/img/bot-avatar.svg";
import userAvatar from "../assets/img/user-avatar.svg";

const footnoteProps = {
  label: 'ChatBot uses AI. Check for mistakes.',
  popover: {
    title: 'Verify information',
    description: `While ChatBot strives for accuracy, AI is experimental and can make mistakes. We cannot guarantee that all information provided by ChatBot is up to date or without error. You should always verify responses using reliable sources, especially for crucial information and decision making.`,
    bannerImage: {
      src: 'https://cdn.dribbble.com/userupload/10651749/file/original-8a07b8e39d9e8bf002358c66fce1223e.gif',
      alt: 'Example image for footnote popover',
    },
    cta: {
      label: 'Dismiss',
      onClick: () => {
        alert('Do something!');
      },
    },
    link: {
      label: 'View AI policy',
      url: 'https://www.redhat.com/',
    },
  },
};

export function Chat() {
  const [availableAgents, setAvailableAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);
  const [conversations, setConversations] = useState<
    Conversation[] | { [key: string]: Conversation[] }
  >([]);
  const [announcement, setAnnouncement] = useState<string>('');
  const [chatSessions, setChatSessions] = useState<ChatSessionSummary[]>([]);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState<boolean>(false);
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null);
  const scrollToBottomRef = React.useRef<HTMLDivElement>(null);
  const historyRef = React.useRef<HTMLButtonElement>(null);

  // Use our custom hook for chat functionality - only when we have a valid agent
  const {
    messages: chatMessages,
    input,
    handleInputChange,
    append,
    isLoading,
    loadSession,
    sessionId,
    attachedFiles,
    handleAttach,
    clearAttachedFiles,
  } = useChat(selectedAgent || 'default', {
    onError: (error: Error) => {
      console.error('Chat error:', error);
      setAnnouncement(`Error: ${error.message}`);
    },
    onFinish: () => {
      setAnnouncement(`Message from assistant complete`);
      if (scrollToBottomRef.current) {
        scrollToBottomRef.current.scrollIntoView({ behavior: 'smooth' });
      }
    },
  });

  const contentToText = (content: InterleavedContent): string => {
    if (content instanceof Array) {
      return content.map(m => contentToText(m)).join('\n');
    }

    if (content.type === 'text') {
      return content.text;
    }

    if (content.type === 'image') {
      // TODO: Display image contents
    }

    return '';
  }

  // Convert our chat messages to PatternFly format
  const messages = React.useMemo(
    () =>
      chatMessages.map(
        (msg): MessageProps => ({
          id: msg.id,
          role: msg.role === 'user' ? 'user' : 'bot',
          content: contentToText(msg.content),
          name: msg.role === 'user' ? 'You' : 'Assistant',
          timestamp: msg.timestamp.toLocaleString(),
          avatar: msg.role === 'user' ? userAvatar : botAvatar,
          avatarProps: { isBordered: true },
          isLoading:
            msg.role === 'assistant' &&
            isLoading &&
            msg.id === chatMessages[chatMessages.length - 1]?.id,
        })
      ),
    [chatMessages, isLoading]
  );

  const displayMode = ChatbotDisplayMode.embedded;

  const onSelectAgent = (
    _event: React.MouseEvent<Element, MouseEvent> | undefined,
    value: string | number | undefined
  ) => {
    if (value) {
      const agentId = value.toString();
      console.log('Agent selected:', agentId);
      setSelectedAgent(agentId);
    }
  };

  const onSelectActiveItem = (
    _e?: React.MouseEvent<Element, MouseEvent>,
    selectedItem?: string | number
  ) => {
    if (!selectedItem || typeof selectedItem !== 'string') return;

    void (async () => {
      try {
        await loadSession(selectedItem);
        setIsDrawerOpen(false); // Close sidebar after selection
      } catch (error) {
        console.error('Error loading session:', error);
        setAnnouncement('Failed to load chat session');
      }
    })();
  };

  const onNewChat = () => {
    if (!selectedAgent) return;

    void (async () => {
      try {
        // Generate unique session name with timestamp
        const timestamp = new Date()
          .toISOString()
          .slice(0, 19)
          .replace(/[-:]/g, '')
          .replace('T', '-');
        const randomSuffix = Math.random().toString(36).substring(2, 6);
        const uniqueSessionName = `Chat-${timestamp}-${randomSuffix}`;

        // Create a new session for the current agent with unique name
        const newSession = await createChatSession(selectedAgent, uniqueSessionName);

        // Load the new session
        await loadSession(newSession.id);

        // Refresh sessions list to include the new session
        await fetchSessionsData(selectedAgent);

        setIsDrawerOpen(false);
      } catch (error) {
        console.error('Error creating new session:', error);
        setAnnouncement('Failed to create new chat session');
      }
    })();
  };

  const handleDeleteSession = useCallback((sessionId: string) => {
    setSessionToDelete(sessionId);
    setIsDeleteModalOpen(true);
  }, []);

  const deleteSessionMutation = useMutation<void, Error, string>({
    mutationFn: (sessionId: string) => {
      if (!selectedAgent) throw new Error('No agent selected');
      return deleteChatSession(sessionId, selectedAgent);
    },
    onSuccess: async () => {
      if (!selectedAgent) return;

      setAnnouncement('Session deleted successfully');
      // Simply refresh sessions data - fetchSessionsData handles everything:
      // - If sessions remain: updates UI and loads first session if current was deleted
      // - If no sessions remain: creates new session, loads it, and updates UI
      await fetchSessionsData(selectedAgent);
    },
    onError: (error) => {
      console.error('Error deleting session:', error);
      setAnnouncement(`Failed to delete session: ${error.message}`);
    },
    onSettled: () => {
      // Always clean up modal state when mutation completes
      setIsDeleteModalOpen(false);
      setSessionToDelete(null);
    },
  });

  const confirmDeleteSession = () => {
    if (!sessionToDelete) return;

    // Trigger the mutation
    deleteSessionMutation.mutate(sessionToDelete);
  };

  const cancelDeleteSession = () => {
    setIsDeleteModalOpen(false);
    setSessionToDelete(null);
  };

  // Create menu items for session actions
  const createSessionMenuItems = useCallback(
    (sessionId: string) => [
      <DropdownList key="session-actions">
        <DropdownItem
          value="Delete"
          id={`delete-${sessionId}`}
          onClick={() => handleDeleteSession(sessionId)}
        >
          Delete
        </DropdownItem>
      </DropdownList>,
    ],
    [handleDeleteSession]
  );

  const findMatchingItems = (targetValue: string) => {
    const filteredConversations = chatSessions.filter((session) =>
      session.title.toLowerCase().includes(targetValue.toLowerCase())
    );

    // Convert to PatternFly conversation format
    const conversations = filteredConversations.map((session) => ({
      id: session.id,
      text: session.title,
      description: session.agent_name,
      timestamp: new Date(session.updated_at).toLocaleDateString(),
      menuItems: createSessionMenuItems(session.id),
    }));

    // append message if no items are found
    if (conversations.length === 0) {
      conversations.push({
        id: '13',
        text: 'No results found',
        description: '',
        timestamp: '',
        menuItems: [],
      });
    }
    return conversations;
  };

  const fetchSessionsData = useCallback(
    async (agentId?: string) => {
      try {
        console.log('fetchSessionsData called with agentId:', agentId);
        const sessions = await fetchChatSessions(agentId);
        console.log('Fetched sessions:', sessions);
        setChatSessions(sessions);

        // Convert to PatternFly conversation format
        const conversations = sessions.map((session) => ({
          id: session.id,
          text: session.title,
          description: session.agent_name,
          timestamp: new Date(session.updated_at).toLocaleDateString(),
          menuItems: createSessionMenuItems(session.id),
        }));

        setConversations(conversations);
        console.log('Set conversations:', conversations);

        // Auto-select first session if no session is currently selected and sessions exist
        // OR if the current sessionId doesn't exist in the fetched sessions (i.e., from different agent)
        console.log('Current sessionId:', sessionId, 'sessions.length:', sessions.length);
        const currentSessionExists =
          sessionId && sessions.some((session) => session.id === sessionId);
        console.log('Current session exists in fetched sessions:', currentSessionExists);

        if ((!sessionId || !currentSessionExists) && sessions.length > 0) {
          const firstSession = sessions[0]; // Sessions should be ordered by updated_at desc (most recent first)
          console.log('Auto-selecting first session:', firstSession.id);
          await loadSession(firstSession.id);
        } else if (sessions.length === 0 && agentId) {
          // Create a new session if agent has no sessions
          try {
            console.log('No sessions found, creating new session for agent:', agentId);
            // Generate unique session name with timestamp
            const timestamp = new Date()
              .toISOString()
              .slice(0, 19)
              .replace(/[-:]/g, '')
              .replace('T', '-');
            const randomSuffix = Math.random().toString(36).substring(2, 6);
            const uniqueSessionName = `Chat-${timestamp}-${randomSuffix}`;

            const newSession = await createChatSession(agentId, uniqueSessionName);
            await loadSession(newSession.id);

            // Update UI state with the new session
            const newSessionSummary: ChatSessionSummary = {
              id: newSession.id,
              title: newSession.title,
              agent_name: newSession.agent_name,
              updated_at: newSession.updated_at,
              created_at: newSession.created_at,
            };
            setChatSessions([newSessionSummary]);

            const conversationObj = {
              id: newSession.id,
              text: newSession.title,
              description: newSession.agent_name,
              timestamp: new Date(newSession.updated_at).toLocaleDateString(),
              menuItems: createSessionMenuItems(newSession.id),
            };
            setConversations([conversationObj]);
          } catch (error) {
            console.error('Error creating initial session:', error);
            setAnnouncement('Failed to create initial session');
          }
        }
      } catch (error) {
        console.error('Error fetching chat sessions:', error);
        setAnnouncement(
          `Failed to fetch sessions: ${error instanceof Error ? error.message : 'Unknown error'}`
        );
      }
    },
    [sessionId, loadSession, setAnnouncement, createSessionMenuItems]
  );

  // Fetch available agents on mount
  useEffect(() => {
    const fetchAgentsData = async () => {
      try {
        console.log('Fetching agents on app load...');
        const agents = await fetchAgents();
        setAvailableAgents(agents);
        if (agents.length > 0) {
          const firstAgent = agents[0].id;
          console.log('Setting first agent:', firstAgent);
          setSelectedAgent(firstAgent);
          // Don't fetch sessions here - let the selectedAgent useEffect handle it
        }
      } catch (err) {
        console.error('Error fetching agents:', err);
        setAnnouncement('Failed to load agents');
      }
    };

    void fetchAgentsData();
  }, []);

  // Handle selectedAgent changes - fetch sessions for the new agent
  useEffect(() => {
    if (selectedAgent) {
      console.log('selectedAgent changed to:', selectedAgent, 'fetching sessions...');
      void fetchSessionsData(selectedAgent);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedAgent]); // fetchSessionsData intentionally excluded to prevent infinite loop

  // Handle message sending
  const handleSendMessage = (message: string | number) => {
    console.log('handleSendMessage called with:', message, 'selectedAgent:', selectedAgent);
    console.log('Current session ID:', sessionId);
    if (typeof message === 'string' && message.trim() && selectedAgent) {
      console.log('Sending message via append:', message, 'using session:', sessionId);
      let contents: Array<TextContentItem | ImageContentItem> = [];
      contents.push({type: 'text', text: message});
      for (const file of attachedFiles) {
        contents.push({type: 'image', image: {data: file}});
      }
      // Add the message to the chat
      append({
        role: 'user',
        content: contents,
      });
      clearAttachedFiles();
    } else {
      console.log('Message not sent - conditions not met:', {
        messageType: typeof message,
        selectedAgent: selectedAgent,
      });
    }
  };

  return (
    <Chatbot displayMode={displayMode}>
      <ChatbotConversationHistoryNav
        displayMode={displayMode}
        onDrawerToggle={() => {
          setIsDrawerOpen(!isDrawerOpen);
        }}
        isDrawerOpen={isDrawerOpen}
        setIsDrawerOpen={setIsDrawerOpen}
        activeItemId={sessionId || undefined}
        onSelectActiveItem={onSelectActiveItem}
        conversations={conversations}
        onNewChat={onNewChat}
        handleTextInputChange={(value: string) => {
          if (value === '') {
            // Convert sessions to conversations format
            const conversations = chatSessions.map((session) => ({
              id: session.id,
              text: session.title,
              description: session.agent_name,
              timestamp: new Date(session.updated_at).toLocaleDateString(),
              menuItems: createSessionMenuItems(session.id),
            }));
            setConversations(conversations);
          }
          const newConversations = findMatchingItems(value);
          setConversations(newConversations);
        }}
        drawerContent={
          <Fragment>
            <ChatbotHeader>
              <ChatbotHeaderMain>
                <ChatbotHeaderMenu
                  ref={historyRef}
                  aria-expanded={isDrawerOpen}
                  onMenuToggle={() => setIsDrawerOpen(!isDrawerOpen)}
                />
                <ChatbotHeaderTitle>Chat</ChatbotHeaderTitle>
              </ChatbotHeaderMain>
              <ChatbotHeaderActions>
                <ChatbotHeaderSelectorDropdown
                  value={
                    availableAgents.find((agent) => agent.id === selectedAgent)?.name ||
                    'Select Agent'
                  }
                  onSelect={onSelectAgent}
                  tooltipContent="Select Agent"
                >
                  <DropdownList>
                    {availableAgents.map((agent) => (
                      <DropdownItem value={agent.id} key={agent.id}>
                        {agent.name}
                      </DropdownItem>
                    ))}
                  </DropdownList>
                </ChatbotHeaderSelectorDropdown>
              </ChatbotHeaderActions>
            </ChatbotHeader>
            <ChatbotContent>
              <MessageBox announcement={announcement}>
                {messages.map((message, index) => {
                  if (index === messages.length - 1) {
                    return (
                      <Fragment key={message.id}>
                        <div ref={scrollToBottomRef}></div>
                        <Message key={message.id} {...message} />
                      </Fragment>
                    );
                  }
                  return <Message key={message.id} {...message} />;
                })}
              </MessageBox>
            </ChatbotContent>
            <ChatbotFooter>
              <MessageBar
                onSendMessage={handleSendMessage as (message: string | number) => void}
                hasMicrophoneButton
                isSendButtonDisabled={isLoading || !selectedAgent}
                value={input}
                onChange={handleInputChange}
                handleAttach={handleAttach}
              />
              <ChatbotFootnote {...footnoteProps} />
            </ChatbotFooter>
          </Fragment>
        }
      ></ChatbotConversationHistoryNav>
      <Modal
        variant={ModalVariant.small}
        title="Confirm Delete"
        isOpen={isDeleteModalOpen}
        onClose={cancelDeleteSession}
      >
        <ModalHeader title="Delete Session" labelId="delete-session-modal-title" />
        <ModalBody id="delete-session-modal-desc">
          Are you sure you want to delete this session?
        </ModalBody>
        <ModalFooter>
          <Button variant="link" onClick={cancelDeleteSession}>
            Cancel
          </Button>
          <Button
            variant="danger"
            isLoading={deleteSessionMutation.isPending}
            onClick={confirmDeleteSession}
          >
            Delete
          </Button>
        </ModalFooter>
      </Modal>
    </Chatbot>
  );
}
