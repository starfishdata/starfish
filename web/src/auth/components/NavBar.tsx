'use client'

import { useState, ReactNode, useEffect, useRef } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import Link from 'next/link'
import { Menu, X, ChevronDown } from 'lucide-react'
import Image from 'next/image'

interface NavBarProps {
  children: ReactNode;
  isSignedIn: boolean;
  inputProjects: any;
}

export default function NavBar({ children, isSignedIn, inputProjects }: NavBarProps) {
  const [projects, setProjects] = useState<any[] | undefined | null>(inputProjects)
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const router = useRouter()
  const dropdownRef = useRef<HTMLButtonElement>(null)
  const pathname = usePathname()
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

  // Check if we're on the homepage, contact page, or blog pages
  const isPinkBackground = pathname === '/' || pathname === '/contactus' || pathname.startsWith('/blog')

  // Add useEffect to sync state when inputProjects changes
  useEffect(() => {
    setProjects(inputProjects)
  }, [inputProjects])

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [])


  return (
    <>
      <nav className={`${
        isPinkBackground 
          ? 'bg-[#FDF2F8]' 
          : 'bg-white'
      }`}>
        <div className="w-full px-3 sm:px-4 md:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            {/* Logo section */}
            <div className="flex">
              <div className="flex items-center">
                <Link href="/">
                  <Image
                    src="/starfish_logo.png"
                    alt="Starfishdata Logo"
                    width={40}
                    height={40}
                  />
                </Link>
              </div>
            </div>

            {/* Desktop Navigation - Hidden on mobile */}
            <div className="hidden md:flex md:items-center md:space-x-4">
              {isSignedIn && (
                <>
                  <Link href="/dashboard" className={`${
                    pathname === '/dashboard'
                      ? 'border-pink-500 text-gray-900'
                      : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                    } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}>
                    Dashboard
                  </Link>
                  
                  <div className="relative">
                    <button 
                      className="relative inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 hover:text-gray-700"
                      onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                    >
                      Projects
                      <ChevronDown className={`ml-1 h-4 w-4 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`} />
                    </button>

                    {isDropdownOpen && (
                      <div className="absolute left-0 mt-2 w-56 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 focus:outline-none z-10">
                        <div className="py-1">
                          {projects?.map((project) => (
                            <Link
                              key={project.id}
                              href={`/project/${project.id}`}
                              className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                              onClick={() => setIsDropdownOpen(false)}
                            >
                              {project.name}
                            </Link>
                          ))}
                          {(!projects || projects.length === 0) && (
                            <div className="px-4 py-2 text-sm text-gray-500">
                              No projects yet
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* {isSignedIn && (
                    <Link href="/api-key-management" className={`${
                      pathname === '/api-key-management'
                        ? 'border-pink-500 text-gray-900'
                        : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                      } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}>
                      API Keys
                    </Link>
                  )} */}
                </>
              )}
              
              <Link href="/contactus" className={`${
                pathname === '/contactus'
                  ? 'border-pink-500 text-gray-900'
                  : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}>
                Contact Us
              </Link>

              <Link href="/blog" className={`${
                pathname === '/blog'
                  ? 'border-pink-500 text-gray-900'
                  : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}>
                Blog
              </Link>

              <a 
                href="https://docs.starfishdata.ai"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center px-1 pt-1 border-b-2 border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 text-sm font-medium"
              >
                API Docs
              </a>
            </div>

            {/* Mobile menu button */}
            <div className="md:hidden flex items-center">
              <button
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                className="inline-flex items-center justify-center p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100"
              >
                {isMobileMenuOpen ? (
                  <X className="block h-6 w-6" />
                ) : (
                  <Menu className="block h-6 w-6" />
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile menu */}
        {isMobileMenuOpen && (
          <div className="md:hidden">
            <div className="pt-2 pb-3 space-y-1">
              {isSignedIn && (
                <>
                  <Link
                    href="/dashboard"
                    className={`${
                      pathname === '/dashboard'
                        ? 'bg-pink-50 border-pink-500 text-pink-700'
                        : 'border-transparent text-gray-500 hover:bg-gray-50 hover:border-gray-300 hover:text-gray-700'
                    } block pl-3 pr-4 py-2 border-l-4 text-base font-medium`}
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    Dashboard
                  </Link>
                  
                  {projects?.map((project) => (
                    <Link
                      key={project.id}
                      href={`/project/${project.id}`}
                      className="block pl-3 pr-4 py-2 border-l-4 border-transparent text-gray-500 hover:bg-gray-50 hover:border-gray-300 hover:text-gray-700 text-base font-medium"
                      onClick={() => setIsMobileMenuOpen(false)}
                    >
                      {project.name}
                    </Link>
                  ))}

                  <Link
                    href="/api-key-management"
                    className={`${
                      pathname === '/api-key-management'
                        ? 'bg-pink-50 border-pink-500 text-pink-700'
                        : 'border-transparent text-gray-500 hover:bg-gray-50 hover:border-gray-300 hover:text-gray-700'
                    } block pl-3 pr-4 py-2 border-l-4 text-base font-medium`}
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    API Keys
                  </Link>
                </>
              )}

              <Link
                href="/contactus"
                className={`${
                  pathname === '/contactus'
                    ? 'bg-pink-50 border-pink-500 text-pink-700'
                    : 'border-transparent text-gray-500 hover:bg-gray-50 hover:border-gray-300 hover:text-gray-700'
                } block pl-3 pr-4 py-2 border-l-4 text-base font-medium`}
                onClick={() => setIsMobileMenuOpen(false)}
              >
                Contact Us
              </Link>

              <Link
                href="/blog"
                className={`${
                  pathname === '/blog'
                    ? 'bg-pink-50 border-pink-500 text-pink-700'
                    : 'border-transparent text-gray-500 hover:bg-gray-50 hover:border-gray-300 hover:text-gray-700'
                } block pl-3 pr-4 py-2 border-l-4 text-base font-medium`}
                onClick={() => setIsMobileMenuOpen(false)}
              >
                Blog
              </Link>

              <a
                href="https://docs.starfishdata.ai"
                target="_blank"
                rel="noopener noreferrer"
                className="block pl-3 pr-4 py-2 border-l-4 border-transparent text-gray-500 hover:bg-gray-50 hover:border-gray-300 hover:text-gray-700 text-base font-medium"
                onClick={() => setIsMobileMenuOpen(false)}
              >
                API Docs
              </a>

            </div>
          </div>
        )}
      </nav>
      {children}
    </>
  )
}