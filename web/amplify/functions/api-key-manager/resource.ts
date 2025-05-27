import { defineFunction } from '@aws-amplify/backend';

export const apiKeyManager = defineFunction({
  name: "api-key-manager",
  timeoutSeconds: 60, // 1 minute timeout
}); 