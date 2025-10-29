# Frontend Development Dockerfile
# Development environment with hot reload capabilities

FROM node:20-alpine

# Set environment variables
ENV NODE_ENV=development \
    NODE_PATH=/app/node_modules \
    PATH=/app/node_modules/.bin:$PATH

# Install additional tools
RUN apk add --no-cache \
    curl \
    git

WORKDIR /app

# Copy application code first (for development with bind mount)
COPY frontend/ .

# Install dependencies
RUN npm install 2>&1 || yarn install 2>&1

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

# Start development server with hot reload
CMD ["npm", "start"]
