# 🛠️ Standalone Developer Tools (`tools/`)

This directory contains standalone Python utilities that developers and SaaS vendors can execute outside or alongside the Django web application.

---

## 📁 Available Tools

### 1. `license_generator.py`
A zero-dependency standalone CLI tool for cryptographically signing and generating commercial software license keys. Can be run from any developer laptop or administrative machine.

#### Usage Examples:
```bash
# 1-Year Commercial License (365 Days)
python tools/license_generator.py --school-code HPS-DELHI --school-name "Horizon Public School" --install-id INST-8841-EC45-0715 --days 365 --plan STANDARD

# Permanent Lifetime Enterprise License
python tools/license_generator.py --school-code HPS-DELHI --school-name "Horizon Public School" --install-id INST-8841-EC45-0715 --lifetime --plan ENTERPRISE

# 30-Day Evaluation Extension
python tools/license_generator.py --school-code HPS-DELHI --days 30 --plan EXTENDED_TRIAL

# Cryptographic Revocation Key (Remote Kill-Switch)
python tools/license_generator.py --school-code HPS-DELHI --revoke
```
