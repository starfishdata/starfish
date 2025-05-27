import { groq } from 'next-sanity'

// Get all posts with basic information
export const allPostsQuery = groq`
*[_type == "post"] | order(publishedAt desc) {
  _id,
  title,
  "slug": slug.current,
  publishedAt,
  excerpt,
  mainImage {
    image {
      asset->{
        _id,
        url,
        metadata {
          dimensions
        }
      }
    }
  }
}`

// Get a single post by slug with all sections
export const postBySlugQuery = groq`
*[_type == "post" && slug.current == $slug][0] {
  _id,
  _createdAt,
  title,
  "slug": slug.current,
  publishedAt,
  excerpt,
  mainImage {
    image {
      asset->{
        _id,
        url,
        metadata
      },
      hotspot,
      crop
    },
    description
  },
  sections[] {
    _type,
    _key,
    _type == "postSection" => {
      sectionTitle,
      sectionImage {
        image {
          asset->{
            _id,
            url,
            metadata
          },
          hotspot,
          crop
        },
        description
      },
      sectionBody[] {
        ...,
        _type == "block" => {
          ...,
          markDefs[]
        }
      }
    },
    _type == "markdownSection" => {
      content
    }
  }
}`

// Get latest posts for homepage or sidebar
export const latestPostsQuery = groq`
*[_type == "post"] | order(publishedAt desc)[0...3] {
  _id,
  title,
  "slug": slug.current,
  publishedAt,
  excerpt,
  mainImage {
    image {
      asset->{
        _id,
        url,
        metadata {
          dimensions
        }
      }
    }
  }
}`

// Get posts by date range
export const postsByDateQuery = groq`
*[_type == "post" && publishedAt >= $startDate && publishedAt <= $endDate] | order(publishedAt desc) {
  _id,
  title,
  "slug": slug.current,
  publishedAt,
  excerpt,
  mainImage {
    image {
      asset->{
        _id,
        url,
        metadata {
          dimensions
        }
      }
    }
  }
}` 