import '../../styles/globals.css'
import { Inter } from "next/font/google";
// import Auth from "../auth/components/Auth";
import NavBar from "../auth/components/NavBar";
//import { isAuthenticated } from "../utils/amplify-server-utils";
import { Toaster } from "@/components/ui/toaster"
import { getAllProjectsOfUser } from '@/src/_actions/actions'
import Script from 'next/script';
import { PostHogProvider } from "@/components/PostHogProvider";

const inter = Inter({ subsets: ["latin"] });

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode,
}) {
  const isSignedIn = true;
  //let projects = isSignedIn ? await getAllProjectsOfUser() : [];
  let projects = await getAllProjectsOfUser();

  return (
    <html lang="en">
      <head>
        <Script
          src="https://getlaunchlist.com/js/widget-diy.js"
          strategy="afterInteractive"
          defer
        />
      </head>
      <body className={inter.className}>
        <PostHogProvider>
          <NavBar {isSignedIn} inputProjects={projects}>
            <div> {/* Adjust padding as needed */}
            {children}
              {/* <Auth>
                
              </Auth> */}
            </div>
            <Toaster />
          </NavBar>
        </PostHogProvider>
      </body>
    </html>
  );
}