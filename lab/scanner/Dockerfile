FROM debian:trixie-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends nmap python3 iproute2 iputils-ping \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /work
CMD ["sleep", "infinity"]
