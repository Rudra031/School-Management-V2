# 🚀 Deployment Configurations Directory (`deploy/`)

This directory contains production deployment scripts, container definitions, web server configuration files, and systemd service templates.

---

## 📁 Directory Structure

```text
deploy/
├── docker/
│   ├── Dockerfile             # Production container image definition
│   └── docker-compose.yml     # Multi-container orchestration (App + PostgreSQL)
├── gunicorn/
│   └── gunicorn.conf.py       # WSGI worker count, binding, logging configs
├── nginx/
│   └── nginx.conf             # Reverse proxy, SSL termination, static routing
├── systemd/
│   └── horizon_sms.service    # Linux systemd background daemon unit
└── README.md                  # Deployment directory overview
```

---

## ⚡ Quick Deployment References

- **Full Runbook**: Refer to [**`docs/DEPLOYMENT_GUIDE.md`**](../../docs/DEPLOYMENT_GUIDE.md) for step-by-step instructions.
- **Docker Compose Setup**:
  ```bash
  cd deploy/docker
  docker-compose up -d --build
  ```
- **Nginx Setup**:
  ```bash
  sudo cp deploy/nginx/nginx.conf /etc/nginx/sites-available/horizon_sms
  sudo ln -s /etc/nginx/sites-available/horizon_sms /etc/nginx/sites-enabled/
  sudo nginx -t && sudo systemctl reload nginx
  ```
- **Systemd Setup**:
  ```bash
  sudo cp deploy/systemd/horizon_sms.service /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable --now horizon_sms
  ```
