# Building Analytics — Frontend (`front`)

Web frontend for the **Building Analytics** platform, built with [Chainlit](https://docs.chainlit.io/) for condominium and community financial analysis.

---

## 📊 What This Application Does

This repository contains the decoupled user-facing web interface that connects residents and administrators with the **Building Analytics Conversational Supervisor**.

### Functional Scope
* **Deep Financial Analysis (`Gastos Comunes`)**: Audits expense structures, variations, anomalies, and category breakdowns across periods.
* **Historical Expense Evolution**: Visualizes and compares how community or unit expenses evolve over time (month-over-month and year-over-year trends).
* **Monthly Building & Unit Queries**: Retrieves specific monthly financial records for the entire condominium or an individual unit (`departamento`/`unidad`).

> **Scope Note**: The platform exclusively analyzes consolidated expense records (`gastos`). It does **not** store or query bank account balances, banking movements, or physical backup receipts/invoices (`boletas`/`facturas`).

### Architecture Overview
* **Web Tier**: Public web interface running Chainlit.
* **Authentication**: Validates user credentials via the Firebase Authentication REST API (`auth.py`) and signs user sessions with a JWT secret (`CHAINLIT_AUTH_SECRET`).
* **Backend Communication**: Calls the backend service over HTTP (`api_client.py`) to process user questions through the Conversational Supervisor.

---

## 📁 Repository Structure

```text
front/
├── .chainlit/
│   └── config.toml                # Chainlit UI, layout, and asset configuration
├── profile/
│   ├── application.yaml           # Base configuration defaults (local development)
│   ├── application-dev.yaml       # DEV environment overrides
│   └── application-prod.yaml      # PROD environment overrides
├── public/
│   ├── custom.css                 # Custom stylesheet & theme styling
│   ├── theme.json                 # Color variables and fonts
│   ├── logo_dark.svg              # Top-left header logo (Dark Mode)
│   ├── logo_light.svg             # Top-left header logo (Light Mode)
│   ├── favicon.svg                # Browser tab icon
│   └── login-hero.svg             # Split-screen login page illustration
├── app.py                         # Main Chainlit application & lifecycle hooks
├── api_client.py                  # HTTP client to Backend API
├── auth.py                        # Firebase Auth verification & role mapping
├── chainlit.md                    # In-app welcome screen text
├── config.py                      # YAML + environment configuration loader
├── models.py                      # Data models shared with backend
├── Dockerfile                     # Container definition
└── requirements.txt               # Python dependencies
```

---

## 💻 Local Development Setup (with `venv`)

### 1. Prerequisites
* **Python 3.11+** installed (`python3 --version`)
* `python3-venv` package installed (on Ubuntu/Debian: `sudo apt update && sudo apt install -y python3-venv`)

### 2. Create and Activate the Virtual Environment (`venv`)

From the `front` directory, create and activate an isolated virtual environment:

```bash
cd ~/agentes/data-analyst-ai-agent/front

# Create the virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate
```

*(To exit the virtual environment later, simply run `deactivate`.)*

### 3. Install Dependencies

With `(.venv)` activated, upgrade `pip` and install the project dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 🔑 How to Get and Configure `CHAINLIT_AUTH_SECRET`

Chainlit requires `CHAINLIT_AUTH_SECRET` (a secret key used to sign and verify session JWT cookies). 

You have two ways to get it, depending on what you want to do:

### Option 1: Generate a New Random Secret for Local Testing (Fastest)
If you just want to run and test the frontend locally on your machine, you don't need GCP access. You can generate a random 32-byte secret using Python:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Copy the generated output and use it as your `CHAINLIT_AUTH_SECRET`.

---

### Option 2: Fetch the Real Secret from Google Cloud Secret Manager
If you want to use the exact secret configured in your cloud environment (e.g. `dev`), fetch it directly using the `gcloud` CLI:

```bash
# Fetch the secret payload from Secret Manager for the dev environment
gcloud secrets versions access latest \
  --secret="building-analytics-chainlit-secret-dev" \
  --project="building-analytics-dev-513719"
```

---

### Setting Up Your Local Environment

Create a `.env` file inside `front/` (this file is ignored by git and will not be committed):

```bash
cat << 'EOF' > .env
APP_ENV=local
CHAINLIT_AUTH_SECRET=<PASTE_YOUR_SECRET_HERE>
BACKEND_API_URL=http://localhost:8080
EOF
```

Replace `<PASTE_YOUR_SECRET_HERE>` with either the generated secret from **Option 1** or the fetched secret from **Option 2**.

---

## ▶️ Running the Application Locally

With `.venv` active, start Chainlit:

```bash
PYTHONPATH=.. chainlit run app.py --port 8000 -w
```

* `PYTHONPATH=..`: Ensures Python finds the `front` module when importing packages.
* `--port 8000`: Runs on port 8000.
* `-w`: Watch mode (automatically reloads the app when you edit code or template files).

Open your browser at:
👉 **[http://localhost:8000/login](http://localhost:8000/login)**
