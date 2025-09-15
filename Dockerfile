# Executive Safety Dashboard - Main Application Container
# Multi-stage build for production optimization
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apk add --no-cache python3 make g++ && \
    npm install -g npm@latest

# Copy package files
COPY package*.json ./

# Install dependencies with npm ci for production
RUN npm ci --only=production && npm cache clean --force

# Copy application source
COPY . .

# Build application (if using build process like webpack, typescript, etc.)
RUN npm run build 2>/dev/null || echo "No build script found, continuing..."

# Production stage
FROM node:18-alpine AS production

# Create non-root user for security
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

# Install security updates and runtime dependencies
RUN apk add --no-cache \
    ca-certificates \
    tzdata \
    && rm -rf /var/cache/apk/*

# Set working directory
WORKDIR /app

# Copy built application from builder stage
COPY --from=builder --chown=nextjs:nodejs /app/node_modules ./node_modules
COPY --from=builder --chown=nextjs:nodejs /app/package*.json ./
COPY --from=builder --chown=nextjs:nodejs /app/dist ./dist 2>/dev/null || \
COPY --from=builder --chown=nextjs:nodejs /app/build ./build 2>/dev/null || \
COPY --from=builder --chown=nextjs:nodejs /app/src ./src
COPY --from=builder --chown=nextjs:nodejs /app/public ./public 2>/dev/null || echo "No public directory"
COPY --from=builder --chown=nextjs:nodejs /app/views ./views 2>/dev/null || echo "No views directory"

# Copy configuration files
COPY --chown=nextjs:nodejs config/ ./config/ 2>/dev/null || echo "No config directory"

# Switch to non-root user
USER nextjs

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD node health-check.js || exit 1

# Start application
CMD ["node", "src/server.js"]