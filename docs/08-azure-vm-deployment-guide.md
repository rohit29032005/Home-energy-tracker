# Azure Linux VM Deployment Guide ☁️

This guide outlines a manual future deployment of the **Home Energy Tracker** microservices platform and React web dashboard onto an **Azure Linux Virtual Machine (VM)** using `docker-compose.prod.yml` and an Nginx reverse proxy. The checked-in production Compose file currently serves HTTP on port 80 only; HTTPS is a separate hardening step, not an already-configured feature.

---

## 🏛️ Deployment Architecture Overview

```text
  Internet Traffic (Port 80; 443 after TLS configuration)
              │
              ▼
    ┌──────────────────┐
    │ Azure VM (Ubuntu)│
    │  Network Security│
    │  Group (NSG)     │
    └─────────┬────────┘
              │
              ▼
   Nginx Reverse Proxy Container (:80; :443 after TLS configuration)
   ├── Serves Static React Dashboard Bundle
   └── Forward /api/* & Service Routes ──► API Gateway Container (:8080)
                                                 │
                   ┌─────────────────────────────┼─────────────────────────────┐
                   ▼                             ▼                             ▼
            User Service (:8081)       Device Service (:8082)       Ingestion Service (:8083)
                   │                             │                             │
                   ▼                             ▼                             ▼
                 MySQL                        MySQL                          Kafka
```

---

## 📋 Prerequisites

1. Active **Azure Account** (Free tier or pay-as-you-go).
2. Registered **Domain Name** (or Azure DNS label e.g., `home-energy.eastus.cloudapp.azure.com`).
3. Local terminal with SSH client installed.

---

## Step 1: Provision the Azure Linux VM

1. Log into the [Azure Portal](https://portal.azure.com/).
2. Click **Create a Resource** ➔ **Virtual Machine**.
3. Configure **Basic Settings**:
   - **Resource Group**: `rg-home-energy-tracker`
   - **Virtual Machine Name**: `vm-home-energy-prod`
   - **Region**: Select your closest region (e.g. `East US` or `West Europe`).
   - **Image**: **Ubuntu Server 22.04 LTS - x64 Gen2**
   - **Size**: **Standard_B2s** (2 vCPUs, 4 GiB RAM) or **Standard_B2ms** (8 GiB RAM recommended).
   - **Authentication**: **SSH public key** (Generate new key pair or select existing).
   - **Username**: `azureuser`
4. Configure **Networking (Inbound Port Rules)**:
   - Allow **SSH (22)**
   - Allow **HTTP (80)**
   - Allow **HTTPS (443)** only after completing the TLS configuration in Step 6
5. Click **Review + Create** and launch the VM.
6. Note down the **Public IP Address** (e.g., `20.120.45.67`).

---

## Step 2: Configure Azure Network Security Group (NSG)

Ensure private infrastructure ports are **NOT** exposed to the internet.

| Port | Protocol | Source | Action | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `22` | TCP | Your IP | Allow | Secure Admin SSH |
| `80` | TCP | Any | Allow | HTTP Web / Certbot SSL challenge |
| `443` | TCP | Any | Allow after TLS setup | Secure HTTPS Web & API traffic |
| `3306`, `8072`, `8080-8086`, `9092` | TCP | Any | **Deny** | Keep databases & microservices internal |

---

## Step 3: Install Docker & Docker Compose on the VM

Connect to your VM via SSH:
```bash
ssh azureuser@<YOUR_VM_PUBLIC_IP>
```

Execute the following setup commands on the VM:
```bash
# 1. Update package list and install system tools
sudo apt-get update && sudo apt-get install -y curl git ufw ca-certificates gnupg

# 2. Add Docker's official GPG key & repository
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 3. Install Docker Engine and Docker Compose plugin
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 4. Add azureuser to docker group (so sudo is not needed for docker commands)
sudo usermod -aG docker azureuser
newgrp docker
```

Verify Docker installation:
```bash
docker --version
docker compose version
```

---

## Step 4: Clone Repository & Configure Environment

```bash
# Clone the repository onto the VM
git clone https://github.com/sahilzambre05/Home-Energy-Tracker.git
cd Home-Energy-Tracker

# Create production .env file from template
cp .env.production.example .env

# Edit .env to set strong production passwords and secret tokens
nano .env
```

Set secure passwords inside `.env`:
```env
MYSQL_ROOT_PASSWORD=YourSuperSecurePassword123!
INFLUX_PASSWORD=YourSuperSecureInfluxPassword123!
INFLUX_TOKEN=YourGenerated64CharacterRandomTokenStringHere
```

---

## Step 5: Launch Production Containers

```bash
# Build images and start all 12 containers in detached mode
docker compose -f docker-compose.prod.yml up -d --build
```

Verify all services are running:
```bash
docker compose -f docker-compose.prod.yml ps
```

Check logs for any service if needed:
```bash
docker compose -f docker-compose.prod.yml logs -f api-gateway
```

---

## Step 6: SSL / HTTPS Configuration (Let's Encrypt & Certbot)

The current `docker-compose.prod.yml` maps only `80:80`, and the current Nginx config has no certificate or `listen 443 ssl` directives. Mounting a certificate alone is not enough to enable HTTPS.

To enable SSL (`https://yourdomain.com`) as a deliberate follow-up:

1. Install Certbot on the host VM:
   ```bash
   sudo apt-get install -y certbot
   ```
2. Temporarily request a certificate using standalone mode:
   ```bash
   sudo certbot certonly --standalone -d <YOUR_DOMAIN_NAME>
   ```
3. Add a certificate mount **and** Nginx TLS server configuration before publishing port 443. The Compose side needs both the certificate volume and a `443:443` port mapping:
   ```yaml
   volumes:
     - /etc/letsencrypt:/etc/letsencrypt:ro
   ports:
     - "443:443"
   ```
4. Update `docker/nginx/nginx.conf` with `listen 443 ssl`, `ssl_certificate`, `ssl_certificate_key`, and the existing `/api/` proxy rules. Test `nginx -t` in the container, reload Nginx, and set up certificate renewal before claiming HTTPS is live.

---

## 🛠️ Maintenance & Operational Commands

### Restart Stack
```bash
docker compose -f docker-compose.prod.yml restart
```

### Stop Production Stack
```bash
docker compose -f docker-compose.prod.yml down
```

### View Application Logs
```bash
docker compose -f docker-compose.prod.yml logs --tail=100 -f
```
