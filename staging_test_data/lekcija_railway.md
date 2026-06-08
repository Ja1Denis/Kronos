# Railway Migracija
    Kada radimo migraciju na Railway, pazite da ne koristite Railpack ako imate Dockerfile.
    Postavite varijablu `RAILWAY_DOCKERFILE_PATH` na `Dockerfile`.
    Pazite da mapirate Persistent Volume na `/app/data`!
    