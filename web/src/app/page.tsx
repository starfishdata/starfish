'use client';

import '@aws-amplify/ui-react/styles.css';
//import outputs from "../../amplify_outputs.json";
import AppPage from '@/components/app-page';

// Amplify.configure(outputs, { ssr: true });

function Homepage() {
  return (
    <AppPage />
  );
}

export default Homepage;
