import { type Schema } from '@/amplify/data/resource';
import { generateServerClientUsingCookies } from '@aws-amplify/adapter-nextjs/data';
import outputs from '@/amplify_outputs.json';
import { cookies } from 'next/headers';
import { createServerRunner } from '@aws-amplify/adapter-nextjs';
import { fetchUserAttributes, getCurrentUser } from 'aws-amplify/auth/server';

export const cookieBasedClient = generateServerClientUsingCookies<Schema>({
  config: outputs,
  cookies,
});

export const { runWithAmplifyServerContext } = createServerRunner({
  config: outputs
});

export const getUser = async () => {
  return await runWithAmplifyServerContext({
    nextServerContext: { cookies },
    async operation(contextSpec) {
      try {
        const user = await fetchUserAttributes(contextSpec);
        return user;
      } catch (err) {
        return null
      }
    }
  })
}

export const isAuthenticated = async () => {
  return await runWithAmplifyServerContext({
    nextServerContext: { cookies },
    async operation(contextSpec) {
      try {
        const user = await getCurrentUser(contextSpec);
        return !!user;
      } catch (err) {
        return false;
      }
    }
  })
}