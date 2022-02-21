# file-picker

[![Docker Image CI](https://github.com/lim1202/file-picker/actions/workflows/docker-image.yml/badge.svg)](https://github.com/lim1202/file-picker/actions/workflows/docker-image.yml)

# Introduction

Move new files by rules.

# How to use

### Preparation

- Edit `config.yaml`, add the rules for moving new files.

### 1. Using docker image

- Change `PATH-TO-CONFIG`, `PATH-TO-SOURCE`, `PATH-TO-TARGET` to your local path

```sh
docker run -d  \
-v /PATH-TO-CONFIG/config.yaml:/app/config.yaml \
-v /PATH-TO-SOURCE/:/source \
-v /PATH-TO-TARGET/:/target \
--restart=always \
lim1202/file-picker:latest
```

### 2. Using docker compose

- Edit `docker-compose.yaml`
- Modify `PATH-TO-CONFIG`, `PATH-TO-SOURCE`, `PATH-TO-TARGET` to your local path
- Copy docker-compose to your server

```sh
docker-compose up -d
```

### 3. Run in local

```sh
python app.py
```
