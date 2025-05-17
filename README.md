# Trading Backend

## Project Overview

This project is a backend service for a trading system. It handles order creation, validation, queueing, and processing using a PostgreSQL database and Redis for job queueing.

## Setup & Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd trading-backend
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables:
   - Create a `.env` file in the project root.
   - Add the following variables:
     ```
     DATABASE_URL=postgresql://postgres:postgres@db:5432/trading_db
     REDIS_URL=redis://redis:6379/0
     ```

## Configuration

- **Database**: PostgreSQL is used for storing orders and related data.
- **Redis**: Used for job queueing and order processing.

## Running the Application

### Using Docker

1. Build and start the services:
   ```bash
   docker-compose up
   ```
2. The application will be available at `http://localhost:8000`.

### Running Locally

1. Start PostgreSQL and Redis services.
2. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## Testing

Run the tests using Docker:

```bash
docker-compose up test
```

## Project Structure

```
trading-backend/
├── app/
│   ├── core/
│   │   ├── database.py
│   │   └── ...
│   ├── handlers/
│   │   ├── order_handler.py
│   │   └── ...
│   ├── models/
│   │   ├── order.py
│   │   └── ...
│   ├── workers/
│   │   ├── order_worker.py
│   │   └── ...
│   └── tests/
│       ├── test_order_flow.py
│       └── ...
├── migrations/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## Key Components

- **OrderHandler**: Manages order creation, validation, and status updates.
- **OrderWorker**: Processes orders from the queue using a broker.
- **Database**: PostgreSQL for data storage.
- **Redis Queue**: Manages job queueing for order processing.

## API Endpoints

- **POST /orders**: Create a new order.
- **GET /orders/{order_id}**: Retrieve an order by ID.
- **PUT /orders/{order_id}**: Update an order's status.

## Troubleshooting

- **Database Connection Issues**: Ensure PostgreSQL is running and the connection string is correct.
- **Redis Connection Issues**: Verify Redis is running and the connection string is correct.
- **Test Failures**: Check the test logs for detailed error messages.

## Integrating with Next.js

1. **Set Up Next.js Project**:

   - Create a new Next.js project:
     ```bash
     npx create-next-app@latest trading-frontend
     cd trading-frontend
     ```
   - Install necessary dependencies:
     ```bash
     npm install axios
     ```

2. **Create API Client**:

   - Create a new file `lib/api.js` to handle API requests:

     ```javascript
     import axios from "axios";

     const API_URL = "http://localhost:8000";

     export const createOrder = async (orderData) => {
       const response = await axios.post(`${API_URL}/orders`, orderData);
       return response.data;
     };

     export const getOrder = async (orderId) => {
       const response = await axios.get(`${API_URL}/orders/${orderId}`);
       return response.data;
     };

     export const updateOrder = async (orderId, orderData) => {
       const response = await axios.put(
         `${API_URL}/orders/${orderId}`,
         orderData
       );
       return response.data;
     };
     ```

3. **Use API Client in Components**:

   - Import and use the API client in your Next.js components to interact with the backend.

4. **Run the Frontend**:
   - Start the Next.js development server:
     ```bash
     npm run dev
     ```
   - The frontend will be available at `http://localhost:3000`.

## Removing Unwanted Folders and Files

- Review the project structure and remove any unused folders or files.
- Ensure the `app/` directory contains only necessary components and tests.
