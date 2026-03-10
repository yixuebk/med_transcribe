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
    Then open `http://127.0.0.1:8000/transcriber/` in a browser. You can also use `localhost` instead of `127.0.0.1` (e.g., `http://localhost:8000/transcriber/`).

## LM Studio Local Server Setup (Optional)

To use a local language model for SOAP note generation instead of (or alongside) the OpenAI API, you can run a model locally through [LM Studio](https://lmstudio.ai/).

### 1. Download a Model

1. Open LM Studio and navigate to the **Model Search** tab (magnifying glass icon on the left sidebar).
2. Search for a medical language model such as `medgemma`.
3. Select an appropriate model variant (e.g., **medgemma-4b-it-GGUF** from lmstudio-community) and click **Download**.

![LM Studio model search — searching for and downloading a MedGemma model](img/lmstudio_model_search.png)

### 2. Adjust Context Max Tokens

1. In the **My Models** tab, select the downloaded model.
2. On the right-hand panel, locate the **Context and Offload** section.
3. Increase the **Context Length** value. The default may be too short for medical transcription SOAP note generation — a value of **10000** tokens or more is suggested, depending on the length of your audio transcripts.

![LM Studio context settings — adjusting the context length for the selected model](img/lmstudio_adjust_context_max_tokens.png)

### 3. Start the Server and Load Models

1. Navigate to the **Developer** tab (code icon on the left sidebar).
2. Toggle the **Status** switch to **Running** to start the local server.
3. Note the **Reachable at** URL (default: `http://127.0.0.1:1234`).
4. Click **+ Load Model** and select your downloaded model. It will appear under **Loaded Models** with a **READY** status once loaded.
5. Ensure the port and model name in this application's `.env` file match the LM Studio server settings.

![LM Studio developer server — running the local server with MedGemma loaded](img/lmstudio_start_server.png)
