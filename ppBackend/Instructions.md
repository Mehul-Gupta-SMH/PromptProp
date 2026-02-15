Read these instructions carefully before coding in ppBackend. This document outlines the core architecture and coding standards for the PromptProp backend, which is responsible for handling the optimization logic, AI interactions, and data management.
This is especially important for the agents that will be making changes to this tool. 

----

## 🛠 Tech Stack
The PromptProp backend is built using the following technologies:
- Python 3.10+,  
- LiteLLM (for interacting with LLM APIs),
- FastAPI (for API layer), 
- SQLAlchemy (for data management), 
- pytest (for testing)
- http files for endpoint testing
- Git for version control
- MLflow for experiment tracking and performance monitoring via a custom-built integration layer 
& visualization dashboard

----

## 🏗 Architecture Overview
The PromptProp backend is structured around a modular design that separates concerns into distinct components. The main modules include:
1. **API Layer**: Handles incoming requests from the frontend and routes them to the appropriate services.
2. **Optimization Engine**: Contains the core logic for the back-propagation process, including prompt generation, evaluation, and refinement.
3. **AI Interaction Module**: Manages all interactions with the Gemini API, including sending prompts and receiving responses.
4. **Data Management**: Responsible for storing and retrieving datasets, optimization histories, and configuration settings.
5. **Utility Functions**: A collection of helper functions for tasks like text processing, performance tracking, and error handling.
6. **Testing Suite**: Contains unit and integration tests to ensure the reliability and correctness of the backend.
7. **Documentation**: Comprehensive documentation for each module, including function signatures, expected inputs/outputs, and usage examples.
8. **Logging and Monitoring**: Implements logging for debugging and monitoring the performance of the backend.
9. **Security and Access Control**: Ensures that API keys and sensitive data are handled securely, with appropriate access controls in place.
10. **Deployment and Scaling**: Guidelines for deploying the backend in a production environment, including considerations for scaling and load balancing.
11. **Error Handling and Recovery**: Strategies for gracefully handling errors and ensuring the system can recover from failures without data loss or corruption.
12. **Performance Optimization**: Techniques for optimizing the performance of the backend, including caching strategies and efficient data processing methods.
13. **Version Control and Collaboration**: Best practices for using version control systems (e.g., Git) and collaborating with other developers on the codebase.
14. **Code Style and Conventions**: Guidelines for maintaining a consistent code style and adhering to best practices in coding standards.
15. **Continuous Integration and Deployment (CI/CD)**: Setting up CI/CD pipelines to automate testing and deployment processes, ensuring that changes are thoroughly tested before being deployed to production.
16. **API Documentation**: Providing clear and comprehensive documentation for the API endpoints, including request/response formats, authentication requirements, and example usage.

----

## 🛠 Coding Standards
To maintain a high-quality codebase, all developers working on the PromptProp backend should adhere to
the following coding standards:
1. **Language**: The backend should be implemented in Python, following the latest version (3.10+).
2. **Code Style**: Follow PEP 8 guidelines for code formatting, including indentation, naming conventions, and line length.
3. **Documentation**: All functions and classes should have docstrings that describe their purpose, parameters, return values, and any exceptions they may raise. Use type hints for function signatures to improve readability and maintainability.
4. **Testing**: Write unit tests for all functions and classes, aiming for at least 80% code coverage. Use a testing framework like pytest and include tests for edge cases and error conditions.
5. **Error Handling**: Implement robust error handling throughout the codebase, using try-except blocks where appropriate and providing meaningful error messages to aid in debugging.
6. **Version Control**: Use Git for version control, with clear commit messages that describe the changes made. Follow a branching strategy (e.g., Git Flow) to manage feature development, bug fixes, and releases.
7. **Code Reviews**: All code changes should be reviewed by at least one other developer before being merged into the main branch. Code reviews should focus on code quality, adherence to coding standards, and overall design.
8. **Security**: Handle sensitive data (e.g., API keys) securely, using environment variables and ensuring that they are not hard-coded in the codebase. Implement appropriate access controls for any APIs or endpoints.
9. **Performance**: Write efficient code that minimizes unnecessary computations and optimizes data processing. Use caching strategies where appropriate to improve performance.
10. **Modularity**: Write modular code that separates concerns and promotes reusability.
11. **Logging**: Implement logging throughout the codebase to aid in debugging and monitoring. Use a consistent logging format and include relevant information (e.g., timestamps, log levels, context).
12. **Continuous Integration**: Set up CI pipelines to automate testing and ensure that all code changes are thoroughly tested before being merged into the main branch. Use tools like GitHub Actions or Jenkins to manage CI processes.

----

