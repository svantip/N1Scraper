# Start postgres container
```
docker run --name postgres_container -p 5432:5432 -v /home/svantip/Scraper/scraper/pgdata:/var/lib/postgresql/data -e POSTGRES_PASSWORD=tockica184 -d postgres
```

# Stop postgres container
```
docker stop postgres_container
docker rm postgres_container
```
