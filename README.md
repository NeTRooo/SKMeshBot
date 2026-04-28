# SKMeshBot

This bot is designed to run using Linux, Docker, docker compose, **USB connect to meshcore node**

## **Build and run bot**

We will find out the port to which the meshcore node is connected.

```bash
ls /dev/ | grep ttyACM
```

The connected meshcore node is displayed. Example: `ttyACM0`

Add the received port to docker-compose.yml `devices` and `environment`

Enter the channel numbers for responses in docker-compose.yml and `environment`

Build and launch a bot:

```bash
docker compose up --build -d
```

To view the logs, use the command:

```bash
docker compose logs -f
```