import { defineFunction } from "@aws-amplify/backend";

export const myApiFunction = defineFunction({
  name: "api-function",
  timeoutSeconds: 60 * 15 // 15 minute timeout
});