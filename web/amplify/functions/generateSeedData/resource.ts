import { defineFunction } from "@aws-amplify/backend"

export const generateSeedData = defineFunction({
  name: "generateSeedData",
  timeoutSeconds: 60 * 15 // 15 minute timeout
})