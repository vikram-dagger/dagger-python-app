# FastAPI Sample Application


## Run the application with Docker Compose

```
docker compose up
```

## Write to the API

```
curl -X POST -H "Content-Type: application/json" -d '{"title": "Dune", "author": "Frank Herbert"}' http://localhost:8000/api/books/
```

## Read from the API

```
curl http://localhost:8000/api/books/
```

## Run tests

```
docker exec -it fastapi_app pytest
```
