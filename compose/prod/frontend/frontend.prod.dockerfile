# Frontend Production Dockerfile
# Multi-stage build for optimized production image

# Build stage
FROM node:20-alpine as builder

# Vacio por defecto: nginx sirve frontend y backend bajo el mismo origen
# (proxy_pass /api/ -> backend), asi que el bundle debe llamar a rutas
# relativas. Solo pasar un valor si el backend vive en otro origen.
ARG REACT_APP_BACKEND_URL=

ENV NODE_ENV=production \
    NODE_PATH=/app/node_modules \
    PATH=/app/node_modules/.bin:$PATH \
    REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL

WORKDIR /app

# Copy source code
COPY frontend/ .

# Install dependencies
RUN npm install 2>&1 || yarn install 2>&1


# Build the React application
RUN npm run build 2>&1 || yarn build 2>&1

# Production stage - serve with Nginx
FROM nginx:alpine

# Copy custom Nginx configuration
COPY compose/nginx.conf /etc/nginx/nginx.conf
COPY compose/prod/nginx-prod.conf /etc/nginx/conf.d/default.conf

# Create non-root user for Nginx
RUN addgroup -g 101 nginx || true && \
    adduser -D -S -h /var/cache/nginx -s /sbin/nologin -G nginx -u 101 nginx || true

# Copy built application from builder
COPY --from=builder /app/build /usr/share/nginx/html

# Create necessary directories
RUN mkdir -p /var/cache/nginx/client_temp && \
    chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chown -R nginx:nginx /var/run/&& \
    chown -R nginx:nginx /etc/nginx/conf.d

USER nginx

EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

# Run Nginx
CMD ["nginx", "-g", "daemon off;"]
