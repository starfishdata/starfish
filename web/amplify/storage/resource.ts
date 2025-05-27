import { defineStorage } from '@aws-amplify/backend';
import { generateSeedData } from '../functions/generateSeedData/resource';

export const storage = defineStorage({
    name: 'seedDataBucket',
    access: (allow) => ({
      'project/*': [
        allow.authenticated.to(['read', 'write', 'delete']),
        allow.resource(generateSeedData).to(['read'])
      ],
    }),
    triggers: {
        onUpload: generateSeedData
    }
  });