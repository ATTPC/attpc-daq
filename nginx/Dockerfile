# Dockerfile for the nginx server

# Use the default container as a base
FROM nginx

# Install our custom config for the Django site
COPY django.conf /etc/nginx/conf.d/

# Remove the default config
RUN rm /etc/nginx/conf.d/default.conf