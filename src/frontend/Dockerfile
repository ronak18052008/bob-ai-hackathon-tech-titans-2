# =============================================================================
# MedBrief AI — Frontend Multi-Stage Production Dockerfile
# Step 15: Production Deployment Configuration
# =============================================================================

# Stage 1: Build production assets
FROM node:20-alpine as builder

WORKDIR /app

# Cache package manifests
COPY src/frontend/package*.json ./
RUN npm ci

# Copy frontend source code
COPY src/frontend ./

# Build optimized production bundle
ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# Stage 2: Production web server
FROM nginx:alpine

# Copy custom nginx configuration with SPA fallback & security headers
COPY src/frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled production artifacts
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD wget -qO- http://localhost/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]
