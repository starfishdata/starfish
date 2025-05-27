'use client';

import { motion } from "framer-motion";
import { Book } from 'lucide-react';

export function AnimatedBlogHeader() {
  return (
    <motion.section 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="text-center py-16 mb-8"
    >
      <div className="flex items-center justify-center space-x-4 mb-6">
        <div className="bg-pink-100 p-4 rounded-full">
          <Book className="h-8 w-8 text-[#DB2777]" />
        </div>
        <h1 className="text-5xl font-bold text-[#DB2777]">
          Our Blog
        </h1>
      </div>
      <p className="text-xl text-gray-600 max-w-2xl mx-auto">
        Explore our latest thoughts, ideas, and insights about synthetic data and AI.
      </p>
    </motion.section>
  );
} 