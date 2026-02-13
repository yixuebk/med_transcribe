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
1. Go to the Django project root (transcriber/be/django_project/) in a terminal.
2. Apply server migrations (create and update database structure) and collect static files (gather user interface stuff).
    ```
    python manage.py migrate
    ```
    ```
    python manage.py collectstatic
    ```
3. Add a file named '.env' in this directory, to place the API key.
    - Place your API key in JSON format as follows:
        ```
        {
            "openai_api_key": "your_key_here"
        }
        ```
4. Start the local server using a terminal
    ```
    waitress-serve --host=127.0.0.1 --port=8000 django_project.wsgi:application
    ```

