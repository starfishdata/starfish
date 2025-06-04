'use client';

import { motion } from "framer-motion";
import Link from "next/link";
import type { SanityDocument } from "next-sanity";

interface BlogPost extends SanityDocument {
  title: string;
  slug: string;
  publishedAt: string;
  excerpt?: string;
  mainImage?: {
    image: {
      asset: {
        _id: string;
        url: string;
        metadata: {
          dimensions: {
            width: number;
            height: number;
          };
        };
      };
    };
  };
}

interface AnimatedBlogCardProps {
  post: BlogPost;
  postImageUrl: string | null;
  index: number;
}

export function AnimatedBlogCard({ post, postImageUrl, index }: AnimatedBlogCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: index * 0.1 }}
    >
      <Link
        href={`/blog/${post.slug}`}
        className="group block bg-white rounded-2xl overflow-hidden shadow-xl hover:shadow-2xl transition-all duration-300"
      >
        {postImageUrl && (
          <div className="aspect-video overflow-hidden">
            <img
              src={postImageUrl}
              alt={post.title}
              className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
              width={post.mainImage?.image?.asset?.metadata?.dimensions?.width || 600}
              height={post.mainImage?.image?.asset?.metadata?.dimensions?.height || 400}
            />
          </div>
        )}
        <div className="p-6 sm:p-8">
          <div className="flex flex-wrap gap-2 mb-4">
            {post.categories?.map((category: string) => (
              <span
                key={category}
                className="px-3 py-1 text-xs font-medium rounded-full bg-pink-100 text-[#DB2777]"
              >
                {category}
              </span>
            ))}
          </div>
          <h2 className="text-2xl font-semibold mb-3 text-gray-900 group-hover:text-[#DB2777] transition-colors">
            {post.title}
          </h2>
          {post.excerpt && (
            <p className="text-gray-600 mb-4 line-clamp-2">
              {post.excerpt}
            </p>
          )}
          <div className="text-sm text-gray-500">
            {new Date(post.publishedAt).toLocaleDateString("en-US", {
              year: "numeric",
              month: "long",
              day: "numeric",
            })}
          </div>
        </div>
      </Link>
    </motion.div>
  );
} 