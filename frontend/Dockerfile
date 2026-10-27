# This Dockerfile is built with the repository root as the Docker build context.
FROM node:20-alpine AS build
WORKDIR /app
ARG VITE_AUTH_ENABLED=true
ENV VITE_AUTH_ENABLED=${VITE_AUTH_ENABLED}
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM nginx:1.25-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY docker/nginx/nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
