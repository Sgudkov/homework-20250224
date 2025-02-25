# Project Description
This project is a Python application that utilizes Redis for data storage. The project includes unit and integration tests written in `tests/unit/test.py` and `tests/integration/test.py`, respectively. The Redis connection is established through the `store.py` module.

# Project Structure
* `tests/unit/test.py`: Unit tests for the application
* `tests/integration/test.py`: Integration tests for the application
* `store.py`: Module for establishing Redis connection

# Dependencies
* `poetry`: Dependency manager
* `pytest`: Testing framework
* `redis`: Redis client library

# Setup and Installation
To set up the project, run the following command:

```bash
make setup
```
This will install the required dependencies using Poetry.

# Running Tests
To run the tests, run the following command:

```bash
make test-unit
```
This will run the tests in `tests/unit/test.py`.

To run the integration tests, execute the following command:
```bash
make test-integration
```
This will run the tests in `tests/integration/test.py`.

# Running the Application
To run the application, execute the following command:
```bash
make run
```
This will start the application using the `api.py` module.

# Redis Connection
The Redis connection is established through the `store.py` module. The connection settings are configured using environment variables.

# Environment Variables
The following environment variables are required:

* `REDIS_PASSWORD`: Redis password
You can set these variables in a `.env` file or using your operating system's environment variable settings.
