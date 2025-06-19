# BasicFIM: Real-Time File Integrity Monitoring Service

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)

A real-time **File Integrity Monitoring (FIM)** microservice designed for modern security platforms. It leverages a powerful monitoring engine to detect file changes instantly and provides a clean REST API for seamless integration with **XDR solutions**.

---

## Table of Contents

- [About The Project](#about-the-project)
- [Key Features](#key-features)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Configuration](#configuration)
- [Running the Project](#running-the-project)
- [Project Structure](#project-structure)
- [License](#license)
- [Contact](#contact)

---

## About The Project

BasicFIM aims to provide a robust and scalable solution for monitoring critical system files and directories. It continuously tracks modifications, creations, or deletions, generating alerts for pre-defined critical files.

Built with a microservices architecture, the core monitoring service is designed to be decoupled, scalable, and easy to maintain.

---

## Key Features

- ✅ **Real-Time Monitoring:** Utilizes OS-native APIs for instant event detection.
- ⚙️ **Configuration-Driven:** Easily define what to monitor and exclude via `config.yaml`.
- 🚀 **High-Performance API:** Built with **FastAPI** for fast, asynchronous event querying.
- 🐳 **Dockerized:** Fully containerized for consistent deployments with Docker and Docker Compose.
- 🌐 **Cross-Platform:** Designed to run on Linux, macOS, and Windows.

---

## Getting Started

Follow these steps to get a local development environment running.

### Prerequisites

Make sure you have the following installed on your system:

-   **Python** (3.9+ recommended)
-   **Docker**
-   **Docker Compose**
-   **Git**

### Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/your_username/BasicFIM.git
    cd BasicFIM
    ```
2.  Navigate to the API service directory:
    ```bash
    cd fim_api_service
    ```
3.  (Optional but Recommended) Create and activate a virtual environment:
    ```bash
    # For macOS/Linux
    python3 -m venv .venv
    source .venv/bin/activate

    # For Windows
    python -m venv .venv
    .\.venv\Scripts\activate
    ```
4.  Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```

---

## Configuration

All application settings are managed in the `config/config.yaml` file. Adjust the paths and settings according to your operating system and monitoring needs.

**`config/config.yaml` example:**

```yaml
fim:
  paths_to_monitor:
    - "/etc"
    - "/var/www"
  critical_files:
    - "/etc/passwd"
    - "/etc/shadow"
  exclude:
    patterns:
      - "*.log"
      - "*.tmp"
    directories:
      - "/proc"
      - "/var/log"
      - "__pycache__"
```

-----

## Running the Project

For simplified usage, we recommend using Docker Compose to run the entire project. This will build the Docker images and start all defined services (API, Database).

From the root directory of the project (`BasicFIM/`):

```bash
docker-compose up --build
```

To run in the background, add the `-d` flag:

```bash
docker-compose up --build -d
```

The FIM API service will be accessible at `http://localhost:8000`. You can view the interactive API documentation (Swagger UI) at `http://localhost:8000/docs`.

-----

## Project Structure

```
BasicFIM/
├── config/
│   └── config.yaml
├── docker-compose.yml
├── fim_api_service/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── fim_scanner/
│       ├── __init__.py
│       ├── main.py
│       ├── core/
│       │   ├── __init__.py
│       │   └── monitor.py
│       ├── database/
│       │   ├── __init__.py
│       │   └── database.py
│       ├── models/
│       │   ├── __init__.py
│       │   └── event_model.py
│       └── settings/
│           ├── __init__.py
│           └── config_loader.py
├── frontend_ui_service/
└── README.md
```

-----

## License

Distributed under the MIT License. See `LICENSE` for more information.

---

## Contact

mail: ekremunalw1@gmail.com

Project Link: [https://github.com/Ekremunalytu/BasicFIM](https://github.com/your_username/BasicFIM)