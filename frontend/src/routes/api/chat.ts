import { convertToModelMessages, streamText } from 'ai'
import { createFileRoute } from '@tanstack/react-router'
import { createOpenAI } from '@ai-sdk/openai'
import type { UIMessage} from 'ai';

const agentScopeRuntime = createOpenAI({
  baseURL: 'http://localhost:8080/compatible-mode/v1',
  apiKey: process.env.CUSTOM_OPENAI_API_KEY || 'EMPTY',
})

export const Route = createFileRoute('/api/chat')({
  server: {
    handlers: {
      POST: async ({ request }) => {
        const { messages }: { messages: Array<UIMessage> } = await request.json()

        const result = streamText({
          // model: glm.chatModel('glm-4.6'),
          model: agentScopeRuntime('agent-model'),
          messages: await convertToModelMessages(messages),
          // onChunk: ({ chunk }) => {
          //   console.log('Chunk:', chunk)
          // },
        })

        return result.toUIMessageStreamResponse()
      },
    },
  },
})
