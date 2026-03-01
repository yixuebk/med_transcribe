# Medical Transcription Project

## Python Virtual Environment Setup
1. Install Python on your system (3.12 or earlier, due to required standard dependencies being removed in 3.13).
2. Using a terminal, create a virtual environment.
    - Linux, specifying Python version in case of multiple versions installed:
        ```
        python3.12 -m venv .venv
        ```
    - Windows, specifying Python version with ```py``` in case of multiple versions installed:
        ```
        py -3.12 -m venv .py3_12_venv
        ```
3. Activate the virtual environment in the current terminal.
    - Linux
        ```
        . .py3_12_venv/bin/activate
        ```
    - Windows PowerShell
        ```
        .\.py3_12_venv\Scripts\activate
        ```
    Note that the commands can be slightly different, such as when using a bash terminal in Windows or activating from a different directory.
    Deactivate Python virtual environments with the command ```deactivate``` when you are done with it.
4. Install required Python modules using ```pip``` and the requirements.txt file.
    - If terminal is in the repository root directory:
        ```
        pip install -r transcriber/requirements.txt
        ```

## Django Application Setup

### Using the bash shell script (Linux)
1. Go to the Django project root (transcriber/be/django_project/) in a terminal.
2. Add a file named '.env' in this directory, to place the API key and local model configuration. Place this config in JSON format as follows:
    ```
    {
        "openai_api_key": "your_key_here",
        "local_llm_api_config": {
            "port": 1234,
            "models": ["your_local_model_here"]
        }
    }
    ```
    > **Tip:** To use local language models for summarization (e.g., MedGemma), you can set up a local AI server using a tool like [LM Studio](https://lmstudio.ai/). Start the local inference server in LM Studio and update the `port` and `models` above to match your LM Studio settings.
3. Run the init_server.sh file to run all necessary commands to set up and start the server
    ```
    ./init_server.sh
    ```

### Run each command manually
1. Go to the Django project root (transcriber/be/django_project/) in a terminal.
2. Add a file named '.env' in this directory, to place the API key and local model configuration. Place this config in JSON format as follows:
    ```
    {
        "openai_api_key": "your_key_here",
        "local_llm_api_config": {
            "port": 1234,
            "models": ["your_local_model_here"]
        }
    }
    ```
    > **Tip:** To use local language models for summarization (e.g., MedGemma), you can set up a local AI server using a tool like [LM Studio](https://lmstudio.ai/). Start the local inference server in LM Studio and update the `port` and `models` above to match your LM Studio settings.
3. Apply server migrations (create and update database structure) and collect static files (gather user interface stuff).
    ```
    python manage.py migrate
    ```
    ```
    python manage.py collectstatic
    ```
4. Start the local server using a terminal
    ```
    waitress-serve --host=127.0.0.1 --port=8000 django_project.wsgi:application
    ```
