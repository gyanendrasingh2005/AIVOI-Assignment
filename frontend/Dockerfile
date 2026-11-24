# Multi-stage Production Dockerfile for PharmaRCA Frontend
# Stage 1: Build static assets
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package descriptors and lockfiles
COPY package.json package-lock.json* pnpm-lock.yaml* ./

# Install dependencies cleanly
RUN if [ -f package-lock.json ]; then npm ci; \
    elif [ -f pnpm-lock.yaml ]; then npm install -g pnpm && pnpm install --frozen-lockfile; \
    else npm install; fi

# Copy source code and build
COPY . .
RUN npm run build

# Stage 2: Serve with secure Alpine Nginx
FROM nginx:1.25-alpine-slim

# Copy custom reverse-proxy and security configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose HTTP
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]

