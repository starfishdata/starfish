'use client'

import '../../styles/globals.css'
import { Inter } from "next/font/google";
import { useEffect, useState, useCallback } from 'react';
// import Auth from "../auth/components/Auth";
import NavBar from "../auth/components/NavBar";
import { Toaster } from "@/components/ui/toaster"
import Script from 'next/script';
const inter = Inter({ subsets: ["latin"] });

export default function RootLayout({
  children,
}: {
  children: React.ReactNode,
}) {
  const [projects, setProjects] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  // Function to fetch projects
  const fetchProjects = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/projects/list', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          userId: "user_67890"
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to fetch projects: ${response.status}`);
      }
      
      const projectsData = await response.json();
      setProjects(projectsData);
    } catch (error) {
      console.error('Error fetching projects:', error);
      setProjects([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial fetch on mount
  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  // Set up real-time updates with polling
  useEffect(() => {
    const interval = setInterval(() => {
      fetchProjects();
    }, 30000); // Refresh every 30 seconds

    return () => clearInterval(interval);
  }, [fetchProjects]);

  // Add visibility change listener for real-time updates
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        fetchProjects();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [fetchProjects]);

  return (
    <html lang="en">
      <head>
        <Script
          src="https://getlaunchlist.com/js/widget-diy.js"
          strategy="afterInteractive"
          defer
        />
        <link rel="stylesheet" href="/amplify-ui.css" />
      </head>
      <body className={inter.className}>
        {/* <PostHogProvider>
          
        </PostHogProvider> */}
        <NavBar isSignedIn={true} inputProjects={projects}>
            <div> {/* Adjust padding as needed */}
            {children}
              {/* <Auth>
                
              </Auth> */}
            </div>
            <Toaster />
          </NavBar>
      </body>
    </html>
  );
}