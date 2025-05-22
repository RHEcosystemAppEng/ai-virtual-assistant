# ai-virtual-assistant

## Clone the repository

1. Clone the ai-virtual-assistant repository

    ```bash
    git clone https://github.com/RHEcosystemAppEng/ai-virtual-assistant
    cd ai-virtual-assistant
    ```

## Start PostgreSQL database

1. Run the following command to start the PostgreSQL

    ```bash
    podman compose --file compose.yaml up --detach
    ```

## Start the backend server

1. Install dependencies:

    ```bash
    python3.10 -m venv venv
    source venv/bin/activate
    pip3 install -r backend/requirements.txt
    ```

2. Start Server

    ```bash
    ./venv/bin/uvicorn backend.main:app
   ```

## Start the ui server

In another terminal:

1. Install dependencies

   ```bash
    cd frontend
    npm install
   ```

2. Start server

   ```bash
    npm run dev
   ```

## Building container image

```bash
podman build --platform linux/amd64 -t quay.io/ecosystem-appeng/ai-virtual-assistant:1.1.0 .
```

## Running container image

1. Start PostgreSQL database
2. Run the container

   ```bash
   podman run --platform linux/amd64 --rm  -p 8000:8000 \
   -e DATABASE_URL=postgresql+asyncpg://admin:password@host.containers.internal:5432/ai_virtual_assistant \
   -e LLAMASTACK_URL=http://host.containers.internal:8321 \
   quay.io/ecosystem-appeng/ai-virtual-assistant:1.1.0
   ```

### Running the container image with compose

* Alternatively, run compose enabling the `deploy-va` profile

   ```bash
   podman compose --profile deploy-va up
   ```
