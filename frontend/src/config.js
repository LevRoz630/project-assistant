// Production: use relative URLs (empty string = same domain)
// Development: use localhost backend
export const API_BASE = import.meta.env.PROD ? '' : 'http://localhost:8000'

// Encode each segment of a path individually for use in URLs
export const encodePath = (p) => p.split('/').map(encodeURIComponent).join('/')
