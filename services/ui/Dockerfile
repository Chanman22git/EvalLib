# Multi-stage: build the static bundle, then serve it with nginx on :3000.
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Browser-facing API URLs (host-published ports). Override via build args if the
# stack is exposed on different hosts/ports.
ARG VITE_GOVERNANCE_API_URL=http://localhost:8001
ARG VITE_ORCHESTRATOR_URL=http://localhost:8002
ARG VITE_PHOENIX_URL=http://localhost:6006
ENV VITE_GOVERNANCE_API_URL=$VITE_GOVERNANCE_API_URL \
    VITE_ORCHESTRATOR_URL=$VITE_ORCHESTRATOR_URL \
    VITE_PHOENIX_URL=$VITE_PHOENIX_URL
RUN npm run build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
