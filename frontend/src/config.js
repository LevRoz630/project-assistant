// Production: use relative URLs (empty string = same domain)
// Development: use localhost backend
export const API_BASE = import.meta.env.PROD ? '' : 'http://localhost:8000'
