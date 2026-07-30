FROM node:20-alpine AS builder

ARG VITE_BUILD_ID
ENV VITE_BUILD_ID=${VITE_BUILD_ID}

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN if [ -n "$VITE_BUILD_ID" ] && [ "$VITE_BUILD_ID" != "dev" ]; then \
      npm run build; \
    else \
      mkdir -p dist && echo "Build skipped: VITE_BUILD_ID not set or is 'dev'." > dist/index.html; \
    fi

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html

COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
