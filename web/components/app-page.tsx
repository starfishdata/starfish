'use client';

import Image from 'next/image'
import { Button } from "@/components/ui/button"
import { useRouter } from 'next/navigation'
import { Database, Cpu, Share2, BarChart3, ChevronDown, Plus, Minus, PlayCircle, Github, Copy, Calendar } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { useState } from 'react'
import Link from 'next/link'

const colorScheme = {
  primary: "#DB2777", // Main pink color for buttons and primary elements
  hover: "#BE185D", // Darker pink for hover states
  text: {
    primary: "#DB2777", // Pink for primary text
    secondary: "#6B7280", // Gray for secondary text
    white: "#FFFFFF" // White text
  },
  background: "#FDF2F8" // Light pink background
};

export default function HomePage() {
  const router = useRouter();
  const [openFaqIndex, setOpenFaqIndex] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);

  const copyCommand = () => {
    navigator.clipboard.writeText('pip install starfish-core');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const faqs = [
    {
      question: "What is Starfishdata's mission in healthcare?",
      answer: "Starfishdata is dedicated to solving the data bottleneck in Healthcare AI by providing high-quality, privacy-preserving synthetic data for research, development, and deployment of AI solutions."
    },
    {
      question: "How does Starfishdata ensure patient privacy?",
      answer: "We use advanced generative models and strict privacy-preserving techniques to ensure that no real patient data is ever exposed or re-identifiable in our synthetic datasets."
    },
    {
      question: "Who can benefit from Starfishdata's solutions?",
      answer: "Healthcare AI startups, hospitals, research institutions, and any organization facing data scarcity or privacy challenges in healthcare can benefit from our synthetic data platform."
    },
    {
      question: "What makes Starfishdata different from other synthetic data providers?",
      answer: "Our exclusive focus on healthcare, deep expertise in generative AI, and commitment to regulatory compliance set us apart. We partner closely with clients to deliver data that accelerates innovation while protecting patient privacy."
    }
  ];

  const toggleFaq = (index: number) => {
    setOpenFaqIndex(openFaqIndex === index ? null : index);
  };

  const scrollToVideo = () => {
    const videoSection = document.getElementById('youtube-video')
    if (videoSection) {
      videoSection.scrollIntoView({ 
        behavior: 'smooth', 
        block: 'start' 
      })
    }
  }

  return (
    <div className="min-h-screen bg-[#FDF2F8] font-sans overflow-x-hidden">
      <motion.header 
        className="min-h-screen flex flex-col items-center justify-center py-10"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        <div className="text-center relative z-10 w-full max-w-2xl mx-auto">
          <motion.div
            className="w-44 h-44 mx-auto mb-8"
            animate={{ 
              y: [0, -10, 0],
              rotate: [0, 5, -5, 0]
            }}
            transition={{ 
              repeat: Infinity,
              duration: 4,
              ease: "easeInOut"
            }}
          >
            <Image
              src="/starfish_logo.png"
              alt="Starfish Logo"
              width={180}
              height={180}
              className="w-full h-full object-contain"
              priority
            />
          </motion.div>
          <motion.h1 
            className="text-4xl sm:text-5xl md:text-6xl font-bold text-[#DB2777] mb-4"
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            Starfishdata
          </motion.h1>
          <motion.p 
            className="text-lg sm:text-xl text-[#6B7280] mb-8 max-w-xl mx-auto font-normal"
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.4 }}
          >
            Solving the data bottleneck in Healthcare AI
          </motion.p>
          {/* Social Links (X, Discord, Hugging Face) */}
          <div className="flex justify-center gap-4 mb-8">
            <Link 
              href="https://github.com/starfishdata/starfish"
              target="_blank"
              className="text-gray-600 hover:text-[#DB2777] transition-colors"
              aria-label="GitHub"
            >
              <Github className="h-5 w-5" />
            </Link>
            <Link 
              href="https://twitter.com/starfishdata"
              target="_blank"
              className="text-gray-600 hover:text-[#DB2777] transition-colors"
              aria-label="Twitter"
            >
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
              </svg>
            </Link>
            <Link 
              href="https://discord.com/invite/qWKmeUtb"
              target="_blank"
              className="text-gray-600 hover:text-[#DB2777] transition-colors"
              aria-label="Discord"
            >
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515a.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0a12.64 12.64 0 0 0-.617-1.25a.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057a19.9 19.9 0 0 0 5.993 3.03a.078.078 0 0 0 .084-.028a14.09 14.09 0 0 0 1.226-1.994a.076.076 0 0 0-.041-.106a13.107 13.107 0 0 1-1.872-.892a.077.077 0 0 1-.008-.128a10.2 10.2 0 0 0 .372-.292a.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127a12.299 12.299 0 0 1-1.873.892a.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028a19.839 19.839 0 0 0 6.002-3.03a.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.956-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.955-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.946 2.418-2.157 2.418z"/>
              </svg>
            </Link>
            <Link 
              href="https://huggingface.co/starfishdata"
              target="_blank"
              className="text-gray-600 hover:text-[#DB2777] transition-colors"
              aria-label="Hugging Face"
            >
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12.025 1.13c-5.77 0-10.449 4.647-10.449 10.378 0 1.112.178 2.181.503 3.185.064-.222.203-.444.416-.577a.96.96 0 0 1 .524-.15c.293 0 .584.124.84.284.278.173.48.408.71.694.226.282.458.611.684.951v-.014c.017-.324.106-.622.264-.874s.403-.487.762-.543c.3-.047.596.06.787.203s.31.313.4.467c.15.257.212.468.233.542.01.026.653 1.552 1.657 2.54.616.605 1.01 1.223 1.082 1.912.055.537-.096 1.059-.38 1.572.637.121 1.294.187 1.967.187.657 0 1.298-.063 1.921-.178-.287-.517-.44-1.041-.384-1.581.07-.69.465-1.307 1.081-1.913 1.004-.987 1.647-2.513 1.657-2.539.021-.074.083-.285.233-.542.09-.154.208-.323.4-.467a1.08 1.08 0 0 1 .787-.203c.359.056.604.29.762.543s.247.55.265.874v.015c.225-.34.457-.67.683-.952.23-.286.432-.52.71-.694.257-.16.547-.284.84-.285a.97.97 0 0 1 .524.151c.228.143.373.388.43.625l.006.04a10.3 10.3 0 0 0 .534-3.273c0-5.731-4.678-10.378-10.449-10.378M8.327 6.583a1.5 1.5 0 0 1 .713.174 1.487 1.487 0 0 1 .617 2.013c-.183.343-.762-.214-1.102-.094-.38.134-.532.914-.917.71a1.487 1.487 0 0 1 .69-2.803m7.486 0a1.487 1.487 0 0 1 .689 2.803c-.385.204-.536-.576-.916-.71-.34-.12-.92.437-1.103.094a1.487 1.487 0 0 1 .617-2.013 1.5 1.5 0 0 1 .713-.174m-10.68 1.55a.96.96 0 1 1 0 1.921.96.96 0 0 1 0-1.92m13.838 0a.96.96 0 1 1 0 1.92.96.96 0 0 1 0-1.92M8.489 11.458c.588.01 1.965 1.157 3.572 1.164 1.607-.007 2.984-1.155 3.572-1.164.196-.003.305.12.305.454 0 .886-.424 2.328-1.563 3.202-.22-.756-1.396-1.366-1.63-1.32q-.011.001-.02.006l-.044.026-.01.008-.03.024q-.018.017-.035.036l-.032.04a1 1 0 0 0-.058.09l-.014.025q-.049.088-.11.19a1 1 0 0 1-.083.116 1.2 1.2 0 0 1-.173.18q-.035.029-.075.058a1.3 1.3 0 0 1-.251-.243 1 1 0 0 1-.076-.107c-.124-.193-.177-.363-.337-.444-.034-.016-.104-.008-.2.022q-.094.03-.216.087-.06.028-.125.063l-.13.074q-.067.04-.136.086a3 3 0 0 0-.135.096 3 3 0 0 0-.26.219 2 2 0 0 0-.12.121 2 2 0 0 0-.106.128l-.002.002a2 2 0 0 0-.09.132l-.001.001a1.2 1.2 0 0 0-.105.212q-.013.036-.024.073c-1.139-.875-1.563-2.317-1.563-3.203 0-.334.109-.457.305-.454m.836 10.354c.824-1.19.766-2.082-.365-3.194-1.13-1.112-1.789-2.738-1.789-2.738s-.246-.945-.806-.858-.97 1.499.202 2.362c1.173.864-.233 1.45-.685.64-.45-.812-1.683-2.896-2.322-3.295s-1.089-.175-.938.647 2.822 2.813 2.562 3.244-1.176-.506-1.176-.506-2.866-2.567-3.49-1.898.473 1.23 2.037 2.16c1.564.932 1.686 1.178 1.464 1.53s-3.675-2.511-4-1.297c-.323 1.214 3.524 1.567 3.287 2.405-.238.839 2.71-1.587 3.216-.642.506.946 3.49 2.056 3.522 2.064 1.29.33 4.568 1.028 5.713-.624m5.349 0c-.824-1.19-.766-2.082.365-3.194 1.13-1.112 1.789-2.738 1.789-2.738s.246-.945.806-.858.97 1.499-.202 2.362c-1.173.864.233 1.45.685.64.451-.812 1.683-2.896 2.322-3.295s1.089-.175.938.647-2.822 2.813-2.562 3.244 1.176-.506 1.176-.506 2.866-2.567 3.49-1.898-.473 1.23-2.037 2.16c-1.564.932-1.686 1.178-1.464 1.53s3.675-2.511 4-1.297c.323 1.214-3.524 1.567-3.287 2.405.238.839 2.71-1.587 3.216-.642.506.946-3.49 2.056-3.522 2.064-1.29.33-4.568 1.028-5.713-.624"/>
              </svg>
            </Link>
          </div>
          {/* Schedule a Call with Us - Main CTA */}
          <Link
            href="https://calendly.com/d/crsb-ckq-fv2/chat-with-starfishdata-team"
            target="_blank"
            className="inline-flex items-center justify-center h-10 px-8 text-sm font-semibold rounded-lg bg-[#DB2777] text-white hover:bg-[#BE185D] transition-all duration-200 mb-8 mx-auto shadow-sm"
          >
            <Calendar className="mr-2 h-5 w-5" />
            Schedule a Call with Us
          </Link>
          {/* Divider below CTA */}
          <div className="w-full flex justify-center mb-8"><div className="w-24 border-t border-gray-200"></div></div>
          {/* Code block for pip install */}
          <div className="relative mb-8 px-2 sm:px-4">
            <div className="text-sm text-gray-500 mb-2">Try our open source library</div>
            <div className="bg-gray-900 rounded-lg p-4 flex justify-between items-center max-w-xs sm:max-w-sm mx-auto">
              <code className="text-white text-sm font-mono">pip install starfish-core</code>
              <button
                onClick={copyCommand}
                className="text-gray-400 hover:text-white transition-colors ml-4"
              >
                {copied ? (
                  <span className="text-green-400 text-sm">Copied!</span>
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>
          {/* Consistent Secondary Buttons under code block */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-8 w-full max-w-md mx-auto">
            <Link 
              href="https://github.com/starfishdata/starfish"
              target="_blank"
              className="sm:min-w-[210px] h-10 px-8 text-sm font-semibold rounded-lg bg-[#DB2777] text-white whitespace-nowrap hover:bg-[#BE185D] transition-all duration-200 flex items-center justify-center"
            >
              <Github className="mr-2 h-5 w-5" />
              Star on GitHub
            </Link>
            <Button 
              type="button"
              className="sm:min-w-[210px] h-10 px-8 text-sm font-semibold rounded-lg bg-white text-[#DB2777] whitespace-nowrap border border-[#DB2777] hover:bg-pink-50 transition-all duration-200 flex items-center justify-center"
              onClick={() => router.push('/signin')}
            >
              Try our managed version
            </Button>
          </div>
          {/* Divider before Supported by section */}
          <div className="w-full flex justify-center mb-8"><div className="w-24 border-t border-gray-200"></div></div>
          {/* Supported by Section (social proof) */}
          <div className="w-full flex flex-col items-center mt-8">
            <h2 className="text-base font-bold text-[#DB2777] mb-2">Supported by</h2>
            <div className="flex flex-row items-center justify-center gap-12">
              <Image
                src="/nvidia.png"
                alt="NVIDIA Inception Partner"
                width={180}
                height={64}
                className="object-contain h-16 w-auto"
              />
              <Image
                src="/microsoft_startups.png"
                alt="Microsoft for Startups"
                width={220}
                height={64}
                className="object-contain h-16 w-auto"
              />
            </div>
          </div>
        </div>
      </motion.header>

      {/* Scroll Indicator Section */}
      <motion.div 
        className="flex justify-center py-8"
        initial={{ opacity: 0, y: -10 }}
        animate={{ 
          opacity: [0, 1, 0],
          y: [0, 10, 0]
        }}
        transition={{ 
          repeat: Infinity,
          duration: 2,
          ease: "easeInOut"
        }}
      >
        <div className="flex flex-col items-center text-pink-600">
          <span className="text-sm font-medium mb-2">Scroll to explore</span>
          <ChevronDown className="h-6 w-6 animate-bounce" />
        </div>
      </motion.div>

      {/* FAQ Section */}
      <section className="py-12 sm:py-24 px-4">
        <motion.h2 
          className="text-4xl font-bold text-[#DB2777] text-center mb-16"
        >
          Frequently Asked Questions
        </motion.h2>

        <div className="max-w-3xl mx-auto">
          {faqs.map((faq, index) => (
            <motion.div
              key={index}
              className="mb-6"
            >
              <button
                className="w-full px-6 py-4 bg-white rounded-2xl flex items-center justify-between text-[#DB2777] hover:bg-pink-50/50 transition-all"
                onClick={() => toggleFaq(index)}
              >
                <span className="text-xl font-medium text-left">{faq.question}</span>
                {openFaqIndex === index ? (
                  <Minus className="w-6 h-6 flex-shrink-0" />
                ) : (
                  <Plus className="w-6 h-6 flex-shrink-0" />
                )}
              </button>
              <AnimatePresence>
                {openFaqIndex === index && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.3 }}
                    className="overflow-hidden"
                  >
                    <div className="px-6 py-4 text-gray-600">
                      <p className="text-lg">{faq.answer}</p>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Footer CTA */}
      <motion.footer 
        className="py-12 sm:py-24 text-center px-4"
      >
        <h2 className="text-4xl font-bold text-[#DB2777] mb-8">
          Ready to Get Started?
        </h2>
        <p className="text-xl text-[#6B7280] mb-12 max-w-2xl mx-auto">
          Join us in revolutionizing AI development with high-quality synthetic data
        </p>
        {/* Add social row above the main footer CTA */}
        <div className="flex justify-center gap-6 mb-8">
          <Link 
            href="https://github.com/starfishdata/starfish"
            target="_blank"
            className="text-gray-400 hover:text-[#DB2777] transition-colors"
            aria-label="GitHub"
          >
            <Github className="h-5 w-5" />
          </Link>
          <Link 
            href="https://twitter.com/starfishdata"
            target="_blank"
            className="text-gray-400 hover:text-[#DB2777] transition-colors"
            aria-label="Twitter"
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
            </svg>
          </Link>
          <Link 
            href="https://discord.com/invite/qWKmeUtb"
            target="_blank"
            className="text-gray-400 hover:text-[#DB2777] transition-colors"
            aria-label="Discord"
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515a.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0a12.64 12.64 0 0 0-.617-1.25a.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057a19.9 19.9 0 0 0 5.993 3.03a.078.078 0 0 0 .084-.028a14.09 14.09 0 0 0 1.226-1.994a.076.076 0 0 0-.041-.106a13.107 13.107 0 0 1-1.872-.892a.077.077 0 0 1-.008-.128a10.2 10.2 0 0 0 .372-.292a.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127a12.299 12.299 0 0 1-1.873.892a.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028a19.839 19.839 0 0 0 6.002-3.03a.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.956-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.955-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.946 2.418-2.157 2.418z"/>
            </svg>
          </Link>
        </div>
        <Button 
          className="px-8 py-3 text-base font-medium rounded-lg bg-[#DB2777] hover:bg-[#BE185D] text-white transition-colors flex items-center justify-center mx-auto"
          onClick={() => window.open('https://calendly.com/d/crsb-ckq-fv2/chat-with-starfishdata-team', '_blank')}
        >
          <Calendar className="mr-2 h-5 w-5" />
          Schedule a Call with Us
        </Button>
      </motion.footer>
    </div>
  )
}