'use client';

import { Authenticator} from '@aws-amplify/ui-react';
import { Amplify } from 'aws-amplify';
import '@aws-amplify/ui-react/styles.css';
import outputs from "../../../amplify_outputs.json";
import { useEffect } from 'react';
import withTheme from '@/src/auth/components/WithTheme';
import { Loader2 } from 'lucide-react'


Amplify.configure(outputs, { ssr: true });

const formFields = {
  signUp: {
    family_name: {
      label: 'Name',
      order: 1
    },
    email: {
      order: 2
    },
    password: {
      order: 3
    }
  },
};

function Signin() {
    useEffect(() => {
        // Disable scrolling when the component is mounted
        document.body.style.overflow = 'hidden';
        
        return () => {
        // Re-enable scrolling when the component is unmounted
        document.body.style.overflow = '';
        };
    }, []);

    return (
        <div
            style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100vh', // Full viewport height
            }}
            >
            <Authenticator formFields={formFields}>
                {({ signOut, user }) => {
                return (
                    <div className="text-center">
                        <div className="flex justify-center mb-4">
                            <Loader2 className="text-pink-600 h-12 w-12 animate-spin" />
                        </div>
                        <p className="text-gray-600">Logging in...</p>
                    </div>
                );
                }}
            </Authenticator>
        </div>
    );
}

// Wrap the Signin component with the withTheme HOC
export default withTheme(Signin);
