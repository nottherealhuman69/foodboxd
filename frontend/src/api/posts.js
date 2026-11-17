// Actions shared by reviews and meals. Backend: routers/posts.py
import { request, path } from './client'
import * as reviews from './reviews'
import * as meals from './meals'

/** postType: 'review' | 'meal' */
export const toggleRepost = (postType, postId) =>
  request(path`/posts/${postType}/${postId}/repost`, { method: 'POST' })

/** commentType: 'review' | 'meal' */
export const toggleCommentLike = (commentType, commentId) =>
  request(path`/comments/${commentType}/${commentId}/like`, { method: 'POST' })

/** The reviews or meals API for a post kind, e.g. forKind('meal').toggleLike(id). */
export const forKind = (kind) => (kind === 'meal' ? meals : reviews)
