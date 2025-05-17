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
  ChatbotWelcomePrompt,
  Conversation,
  Message,
  MessageBar,
  MessageBox,
  MessageProps,
} from '@patternfly/chatbot';
import { DropdownItem, DropdownList } from '@patternfly/react-core';
import baseUrl from '../config/api';
// import botAvatar from "../assets/img/bot-avatar.svg";
// import userAvatar from "../assets/img/user-avatar.svg";
import React, { Fragment, useEffect } from 'react';

interface LlamaMessage {
  role: 'user' | 'assistant';
  content: string;
}

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

const fillerWelcomePrompts = [
  {
    title: 'Set up account',
    message: 'Choose the necessary settings and preferences for your account.',
  },
  {
    title: 'Troubleshoot issue',
    message: 'Find documentation and instructions to resolve your issue.',
  },
];

const fillerInitialConversations: Conversation[] = [
  { id: '1', text: 'Hello, can you give me an example of what you can do?' },
  {
    id: '2',
    text: 'Enterprise Linux installation and setup',
  },
  { id: '3', text: 'Troubleshoot system crash' },
  { id: '4', text: 'Ansible security and updates' },
  { id: '5', text: 'Red Hat certification' },
  { id: '6', text: 'Lightspeed user documentation' },
  { id: '7', text: 'Crashing pod assistance' },
  { id: '8', text: 'OpenShift AI pipelines' },
  { id: '9', text: 'Updating subscription plan' },
  { id: '10', text: 'Red Hat licensing options' },
  { id: '11', text: 'RHEL system performance' },
  { id: '12', text: 'Manage user accounts' },
];

interface LlamaModel {
  id: string;
  name: string;
  model_type: string;
}

export function AssistantChat() {
  const [messages, setMessages] = React.useState<MessageProps[]>([]);
  const [availableModels, setAvailableModels] = React.useState<LlamaModel[]>([]);
  const [selectedModel, setSelectedModel] = React.useState('');
  const [isSendButtonDisabled, setIsSendButtonDisabled] = React.useState(false);
  const [isDrawerOpen, setIsDrawerOpen] = React.useState(false);
  const [conversations, setConversations] = React.useState<
    Conversation[] | { [key: string]: Conversation[] }
  >(fillerInitialConversations);
  const [announcement, setAnnouncement] = React.useState<string>();
  const scrollToBottomRef = React.useRef<HTMLDivElement>(null);
  const historyRef = React.useRef<HTMLButtonElement>(null);

  const displayMode = ChatbotDisplayMode.embedded;

  const onSelectModel = (
    _event: React.MouseEvent<Element, MouseEvent> | undefined,
    value: string | number | undefined
  ) => {
    setSelectedModel(value as string);
  };
  const findMatchingItems = (targetValue: string) => {
    const filteredConversations = fillerInitialConversations.filter((convo) =>
      convo.text.includes(targetValue)
    );

    // append message if no items are found
    if (filteredConversations.length === 0) {
      filteredConversations.push({
        id: '13',
        noIcon: true,
        text: 'No results found',
      });
    }
    return filteredConversations;
  };

  //TODO: REPLACE THIS WITH ACTUAL IDs
  const generateId = () => {
    const id = Date.now() + Math.random();
    return id.toString();
  };

  // Fetch available models on mount
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await fetch(`${baseUrl}/llama_stack/llms`);
        const models = await response.json();
        const llmModels = models.filter((model: LlamaModel) => model.model_type === 'llm');
        setAvailableModels(llmModels);
        if (llmModels.length > 0) {
          setSelectedModel(llmModels[0].id);
        }
      } catch (err) {
        console.error('Error fetching models:', err);
        setAnnouncement('Failed to load LLM models');
      }
    };
    fetchModels();
  }, []);

  const handleSend = async (message: string) => {
    if (!selectedModel || !message.trim()) return;

    setIsSendButtonDisabled(true);
    const newMessages: MessageProps[] = [];

    // Add user message
    newMessages.push({
      id: generateId(),
      role: 'user',
      content: message,
      name: 'You',
      timestamp: new Date().toLocaleString(),
      avatar: '',
      avatarProps: { isBordered: true },
    });

    // Add assistant message
    const assistantMessageId = generateId();
    newMessages.push({
      id: assistantMessageId,
      role: 'bot',
      content: '',
      name: 'Assistant',
      isLoading: true,
      timestamp: new Date().toLocaleString(),
      avatar: '',
      avatarProps: { isBordered: true },
    });

    // Update messages state
    setMessages((prevMessages) => [...prevMessages, ...newMessages]);

    try {
      // Convert messages to LlamaStack format
      const llamaMessages: LlamaMessage[] = messages
        .concat(newMessages)
        .filter((msg) => !msg.isLoading)
        .map((msg) => ({
          role: msg.role === 'user' ? 'user' : 'assistant',
          content: msg.content || '',
        }));

      // Stream response from LlamaStack
      const response = await fetch(`${baseUrl}/llama_stack/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: selectedModel,
          messages: llamaMessages,
          stream: true,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No reader available');

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          // Decode the chunk and process any complete SSE messages
          const chunk = new TextDecoder().decode(value, { stream: true });
          const lines = chunk.split('\n\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const text = line.slice(6);
              if (text.trim() === '[DONE]') {
                break;
              } else if (text.trim().startsWith('Error:')) {
                throw new Error(text.trim().slice(7));
              } else if (text) {
                // Update message content
                setMessages((prev) => {
                  const updated = [...prev];
                  const lastMsg = updated.find((msg) => msg.id === assistantMessageId);
                  if (lastMsg) {
                    // Add space after sentence endings if needed
                    const currentContent = lastMsg.content || '';
                    const needsSpace =
                      currentContent.match(/[.!?]$/) && text && !text.startsWith(' ');
                    lastMsg.content = currentContent + (needsSpace ? ' ' : '') + text;
                    lastMsg.isLoading = false;
                  }
                  return updated;
                });

                // Scroll to bottom
                if (scrollToBottomRef.current) {
                  scrollToBottomRef.current.scrollIntoView({ behavior: 'smooth' });
                }
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
      }
      setAnnouncement(`Message from Bot: API response goes here`);
      setIsSendButtonDisabled(false);
    } catch (error) {
      console.error('Error sending message:', error);
      setAnnouncement('Failed to send message');
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
        activeItemId="1"
        onSelectActiveItem={(_e, selectedItem) =>
          console.log(`Selected history item with id ${selectedItem}`)
        }
        conversations={conversations}
        onNewChat={() => {
          setIsDrawerOpen(!isDrawerOpen);
          setMessages([]);
        }}
        handleTextInputChange={(value: string) => {
          if (value === '') {
            setConversations(fillerInitialConversations);
          }
          // this is where you would perform search on the items in the drawer
          // and update the state
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
                <ChatbotHeaderSelectorDropdown value={selectedModel} onSelect={onSelectModel}>
                  <DropdownList>
                    {availableModels.map((model) => (
                      <DropdownItem value={model.id} key={model.id}>
                        {model.name}
                      </DropdownItem>
                    ))}
                  </DropdownList>
                </ChatbotHeaderSelectorDropdown>
              </ChatbotHeaderActions>
            </ChatbotHeader>
            <ChatbotContent>
              {/* Update the announcement prop on MessageBox whenever a new message is sent
                 so that users of assistive devices receive sufficient context  */}
              <MessageBox announcement={announcement}>
                <ChatbotWelcomePrompt
                  title="Hi, ChatBot User!"
                  description="How can I help you today?"
                  prompts={fillerWelcomePrompts}
                />
                {/* This code block enables scrolling to the top of the last message.
                  You can instead choose to move the div with scrollToBottomRef on it below 
                  the map of messages, so that users are forced to scroll to the bottom.
                  If you are using streaming, you will want to take a different approach; 
                  see: https://github.com/patternfly/chatbot/issues/201#issuecomment-2400725173 */}
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
                onSendMessage={(message) => handleSend(message as string)}
                hasMicrophoneButton
                isSendButtonDisabled={isSendButtonDisabled}
              />
              <ChatbotFootnote {...footnoteProps} />
            </ChatbotFooter>
          </Fragment>
        }
      ></ChatbotConversationHistoryNav>
    </Chatbot>
  );
}
