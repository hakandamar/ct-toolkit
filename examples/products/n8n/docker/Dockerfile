FROM n8nio/n8n:latest

USER root

# Create a dedicated directory for custom extensions that will not be overwritten by volumes
RUN mkdir -p /custom-extensions && chown -R node:node /custom-extensions

# Copy the custom node source code
COPY --chown=node:node custom-node /custom-node-src

USER node
# Install dependencies and build the TypeScript code into dist
RUN cd /custom-node-src && \
    npm install --include=dev && \
    npm run build && \
    mkdir -p dist/nodes/CtToolkit && \
    cp nodes/CtToolkit/cttoolkit.svg dist/nodes/CtToolkit/

# Install the custom node package into the custom extensions directory so N8N finds it
RUN cd /custom-extensions && \
    npm install /custom-node-src