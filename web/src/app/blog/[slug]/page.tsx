import { PortableText, type PortableTextComponents, type SanityDocument } from "next-sanity";
import { client } from "../../../sanity/client";
import Link from "next/link";
import { ArrowLeft } from 'lucide-react';
import styles from '../styles.module.css';
import { postBySlugQuery } from '../queries';
import ReactMarkdown from 'react-markdown';
import type { Components } from 'react-markdown';
import React from 'react';

const options = { next: { revalidate: 30 } };

// Define custom PortableText components to adjust heading levels
const portableTextComponents: Partial<PortableTextComponents> = {
  block: {
    h1: ({value, children}) => <h3 className="text-3xl font-bold mt-8 mb-4">{children}</h3>,
    h2: ({value, children}) => <h4 className="text-2xl font-bold mt-6 mb-3">{children}</h4>,
    h3: ({value, children}) => <h5 className="text-xl font-bold mt-4 mb-2">{children}</h5>,
    h4: ({value, children}) => <h6 className="text-lg font-bold mt-4 mb-2">{children}</h6>,
  }
};

interface SanityImage {
  asset: {
    _id: string;
    url: string;
    metadata: {
      dimensions?: {
        width: number;
        height: number;
        aspectRatio: number;
      };
    };
  };
  hotspot?: { x: number; y: number };
  crop?: { top: number; bottom: number; left: number; right: number };
}

interface ImageWithDescription {
  image: SanityImage;
  description: string | null;
}

interface PostSection {
  _type: 'postSection';
  _key: string;
  sectionTitle?: string | null;
  sectionImage?: ImageWithDescription;
  sectionBody: any[];
}

interface MarkdownSection {
  _type: 'markdownSection';
  _key: string;
  content: string;
}

type Section = PostSection | MarkdownSection;

interface BlogPost extends SanityDocument {
  _id: string;
  _createdAt: string;
  title: string;
  slug: string;
  publishedAt: string;
  excerpt?: string;
  mainImage?: ImageWithDescription;
  sections?: Section[];
}

// Function to render a regular post section
function RenderPostSection({ section }: { section: PostSection }) {
  return (
    <div key={section._key} className="mb-20">
      {section.sectionTitle && (
        <h2 className="text-4xl sm:text-5xl font-bold text-gray-900 mb-10 leading-tight">
          {section.sectionTitle}
        </h2>
      )}

      {section.sectionImage?.image?.asset?.url && (
        <figure className="mb-12">
          <img
            src={section.sectionImage.image.asset.url}
            alt={section.sectionImage.description || section.sectionTitle || 'Section image'}
            className="w-full rounded-xl shadow-md"
            width={section.sectionImage.image.asset.metadata?.dimensions?.width || 1200}
            height={section.sectionImage.image.asset.metadata?.dimensions?.height || 675}
          />
          {section.sectionImage.description && (
            <figcaption className="mt-4 text-sm text-gray-500 italic text-center">
              {section.sectionImage.description}
            </figcaption>
          )}
        </figure>
      )}

      <div className="prose prose-lg prose-pink max-w-none">
        <PortableText 
          value={section.sectionBody}
          components={portableTextComponents}
        />
      </div>
    </div>
  );
}

// Function to render a markdown section
function RenderMarkdownSection({ section }: { section: MarkdownSection }) {

  if (!section.content) {
    console.warn('Markdown section has no content:', section._key);
    return null;
  }

  const markdownComponents: Components = {
    h1: ({node, ...props}) => (
      <h2 className="text-4xl sm:text-5xl font-bold text-gray-900 mb-10 leading-tight" {...props} />
    ),
    h2: ({node, ...props}) => (
      <h3 className="text-3xl font-bold mt-8 mb-4" {...props} />
    ),
    h3: ({node, ...props}) => (
      <h4 className="text-2xl font-bold mt-6 mb-3" {...props} />
    ),
    h4: ({node, ...props}) => (
      <h5 className="text-xl font-bold mt-4 mb-2" {...props} />
    ),
    // Handle images outside of paragraphs
    p: ({node, children, ...props}) => {
      // Check if the only child is an img element
      const hasOnlyImage = React.Children.toArray(children).every(
        child => React.isValidElement(child) && child.type === 'img'
      );

      // If it's just an image, don't wrap in <p>
      if (hasOnlyImage) {
        return <>{children}</>;
      }

      return <p className="mb-6 text-gray-700" {...props}>{children}</p>;
    },
    // Handle images with custom figure wrapper
    img: ({node, src, alt}) => (
      <figure className="my-8">
        <img
          src={src || ''}
          alt={alt || ''}
          className="w-full rounded-xl shadow-md"
          loading="lazy"
        />
        {alt && (
          <figcaption className="mt-4 text-sm text-gray-500 italic text-center">
            {alt}
          </figcaption>
        )}
      </figure>
    ),
    // Add blockquote styling
    blockquote: ({node, ...props}) => (
      <blockquote className="border-l-4 border-pink-500 pl-4 italic my-6" {...props} />
    ),
    // Add list styling
    ul: ({node, ...props}) => (
      <ul className="list-disc list-inside mb-6" {...props} />
    ),
    ol: ({node, ...props}) => (
      <ol className="list-decimal list-inside mb-6" {...props} />
    ),
  };

  return (
    <div key={section._key} className="mb-20">
      <div className="prose prose-lg prose-pink max-w-none">
        <ReactMarkdown components={markdownComponents}>
          {section.content}
        </ReactMarkdown>
      </div>
    </div>
  );
}

export default async function PostPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const post = await client.fetch<BlogPost>(postBySlugQuery, await params, options);
  
  if (!post) {
    return (
      <div className="min-h-screen bg-[#FDF2F8] flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Post not found</h1>
          <Link 
            href="/blog" 
            className="text-[#DB2777] hover:text-pink-700 transition-colors"
          >
            Return to blog
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FDF2F8]">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
        <nav className="mb-16">
          <Link 
            href="/blog" 
            className="inline-flex items-center text-[#DB2777] hover:text-pink-700 transition-colors group text-lg"
          >
            <ArrowLeft className="h-5 w-5 mr-2 transition-transform group-hover:-translate-x-1" />
            Back to Blog
          </Link>
        </nav>

        <article className="max-w-4xl mx-auto">
          <header className="text-center mb-20">
            <h1 className="text-5xl sm:text-6xl font-bold text-gray-900 mb-8 leading-tight">
              {post.title}
            </h1>
            
            {post.excerpt && (
              <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
                {post.excerpt}
              </p>
            )}

            <time className="text-base text-gray-500 block">
              {new Date(post.publishedAt).toLocaleDateString("en-US", {
                year: "numeric",
                month: "long",
                day: "numeric",
              })}
            </time>

            {post.mainImage?.image?.asset?.url && (
              <figure className="mt-16">
                <img
                  src={post.mainImage.image.asset.url}
                  alt={post.mainImage.description || post.title}
                  className="w-full rounded-2xl shadow-lg"
                  width={post.mainImage.image.asset.metadata?.dimensions?.width || 1200}
                  height={post.mainImage.image.asset.metadata?.dimensions?.height || 675}
                />
                {post.mainImage.description && (
                  <figcaption className="mt-4 text-sm text-gray-500 italic text-center">
                    {post.mainImage.description}
                  </figcaption>
                )}
              </figure>
            )}
          </header>

          <div className={styles.blogContent}>
            {post.sections?.map((section) => {
              if (!section._type) {
                console.warn('Section missing _type:', section);
                return null;
              }
              return section._type === 'markdownSection' 
                ? <RenderMarkdownSection key={section._key} section={section as MarkdownSection} />
                : <RenderPostSection key={section._key} section={section as PostSection} />;
            })}
          </div>
        </article>
      </div>
    </div>
  );
}