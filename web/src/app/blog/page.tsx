import { client } from "../../sanity/client";
import type { SanityDocument } from "next-sanity";
import { AnimatedBlogCard } from "../../components/ui/animated-blog-card";
import { AnimatedBlogHeader } from "../../components/ui/animated-blog-header";
import { allPostsQuery } from './queries';

const options = { next: { revalidate: 30 } };

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

export default async function BlogPage() {
  const posts = await client.fetch<BlogPost[]>(allPostsQuery, {}, options);

  return (
    <div className="min-h-screen bg-[#FDF2F8]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <AnimatedBlogHeader />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 pb-16">
          {posts.map((post, index) => (
            <AnimatedBlogCard
              key={post._id}
              post={post}
              postImageUrl={post.mainImage?.image?.asset?.url || null}
              index={index}
            />
          ))}
        </div>

        {posts.length === 0 && (
          <div className="text-center py-16 bg-white rounded-2xl shadow-xl mb-16">
            <div className="bg-pink-100 p-4 rounded-full w-16 h-16 mx-auto mb-4 flex items-center justify-center">
              <svg
                className="h-8 w-8 text-[#DB2777]"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9.5a2.5 2.5 0 00-2.5-2.5H15"
                />
              </svg>
            </div>
            <h2 className="text-2xl font-semibold text-gray-900 mb-2">No Posts Yet</h2>
            <p className="text-gray-600">
              Check back soon for our latest articles and insights.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}