FROM python:3.10-slim

RUN sed -i \
's@deb.debian.org@mirrors.tuna.tsinghua.edu.cn@g' \
/etc/apt/sources.list.d/debian.sources

RUN apt update && \
    apt install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app
