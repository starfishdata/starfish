export const openAIModels = [
  { value: 'gpt-4o-2024-08-06' },
  { value: 'gpt-4o-mini-2024-07-18' },
  { value: 'gpt-4-0613' },
  { value: 'gpt-3.5-turbo-0125' },
  { value: 'gpt-3.5-turbo-1106' },
  { value: 'gpt-3.5-turbo-0613' },
]

export const factories = [
  { id: 'factory-1', name: 'Factory 1' },
  { id: 'factory-2', name: 'Factory 2' }
]

export const schemaExample = JSON.stringify({
  question: 'string',
  answer: 'string'
}, null, 2); 