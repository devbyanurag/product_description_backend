# iSEP-ContentGenerationML

## Prerequisites
* Python 3.x installed on your system.
* Obtain a Hugging Face API token. If you don't have one, follow these steps:
    - 1: Go to Hugging Face Settings - API Tokens.
    - 2: Log in or create a new account.
    - 3: Create a new token.
    - 4: Copy the generated token.
* Obtain OpenAi API key.

* create two variable in .env HUGGINGFACE_TOKEN and OPENAI_API_KEY. Assign the values which you get from above steps.

## Setup Virtual Environment

1: Open your terminal or command prompt.

2: Navigate to the root directory of your project.

3: Run the following commands to create a virtual environment:

```  python -m venv venv```

``` venv\Scripts\activate ```

## Install Dependencies

1: Make sure your virtual environment is activated.

2: Run the following command to install the required dependencies:

```  pip install -r requirements.txt ```

## Set Environment Variables
Set the following environment variables for your project:

(HUGGINGFACE_TOKEN): Obtain your Hugging Face API token and set it as an environment variable name as "HUGGINGFACE_TOKEN"

## Run the Application
With the virtual environment activated, run the following command to start the application:

``` python main.py ```

``` uvicorn main:app --host 0.0.0.0 --port 10000```