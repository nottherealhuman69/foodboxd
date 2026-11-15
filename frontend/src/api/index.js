// Usage:  import * as api from '../api'
//         const res = await api.reviews.toggleLike(id)
//
// One file per backend router (backend/app/routers/), named the same where possible.

export * as auth from './auth'
export * as reviews from './reviews'
export * as meals from './meals'
export * as posts from './posts'
export * as users from './users'
export * as social from './social'
export * as feed from './feed'
export * as places from './places'
export * as trylist from './trylist'
export * as lists from './lists'
export * as groupLists from './groupLists'
export * as notifications from './notifications'
export { session } from './session'
