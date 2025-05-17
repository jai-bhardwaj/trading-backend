#!/bin/bash

# Run the initialization script inside the web container
docker-compose exec web python -m app.scripts.init_strategies 