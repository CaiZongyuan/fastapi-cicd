import { streamText, UIMessage, convertToModelMessages } from 'ai'
import { createOpenAICompatible } from '@ai-sdk/openai-compatible'
import { createFileRoute } from '@tanstack/react-router'
import { createOpenAI } from '@ai-sdk/openai'

const agentScopeRuntime = createOpenAI({
  baseURL: 'http://localhost:8090/compatible-mode/v1',
  apiKey: process.env.CUSTOM_OPENAI_API_KEY || 'EMPTY',
})

const glm = createOpenAICompatible({
  name: 'glm',
  apiKey: process.env.GLM_API_KEY,
  baseURL: 'https://open.bigmodel.cn/api/coding/paas/v4',
})

export const Route = createFileRoute('/api/chat')({
  server: {
    handlers: {
      POST: async ({ request }) => {
        const { messages }: { messages: UIMessage[] } = await request.json()

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
