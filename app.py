from flask import Flask, request, jsonify
import json
from openai import AzureOpenAI
from flasgger import Swagger, swag_from
from flask_swagger_ui import get_swaggerui_blueprint
from flask_cors import CORS  # Import CORS
# Initialize the Azure OpenAI API client
llm = AzureOpenAI(
    azure_endpoint="https://genral-openai.openai.azure.com/",
    api_key="8929107a6a6b4f37b293a0fa0584ffc3",
    api_version="2024-02-01"
)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # This will allow cross-origin requests to all routes


# Swagger UI setup
SWAGGER_URL = '/api/docs'  # URL for exposing Swagger UI (without trailing '/')
API_URL = '/static/swagger.json'  # Our API url (can of course be a local resource)

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,  # Swagger UI static files will be mapped to '{SWAGGER_URL}/dist/'
    API_URL,
    config={  # Swagger UI config overrides
        'app_name': "AutoML APIs"
    }
)

app.register_blueprint(swaggerui_blueprint)

# Swagger configuration
swagger = Swagger(app, template={
    "info": {
        "title": "AutoML APIs",
        "description": "API for Automated Machine Learning tool",
        "version": "1.0.0"
    },
    "host": "reportsectionsapi-f7a8f7a9ecc8d5ce.eastus-01.azurewebsites.net",  # Change to your host if needed
    "basePath": "/",  # Base path for API
})

# Function to update an Arabic article in JSON format
def update_arabic_article(article_json, arabic_prompt):
    """
    Updates an Arabic article in JSON format based on a provided Arabic prompt using GPT-4.

    Parameters:
        article_json (str): The original article in JSON format as a string.
        arabic_prompt (str): The Arabic prompt to instruct the model to edit or enhance the article.

    Returns:
        dict: A dictionary containing the updated article or an error message.
    """
    conversation_history = [
        {
            "role": "system",
            "content": """You are a professional journalist tasked with editing and enhancing an Arabic article structure.
                          The article is structured in a JSON format and you should return the updated JSON with the changes without changing the style of the input json as the content should begin with"هذه النقطة لهذا العنوان ستتحدث عن".
                          Follow the user-provided prompt and make necessary adjustments.
                          Be sure that the output was JSON fromatted not String Formatted
                          Be sure that the headings contains a large list that contains listItmesList list & listItems list.
                          Be sure that the headings in the output Json file was array of objects not array of arrays.
                          """
        },
        {
            "role": "system",
            "content": """
             انت مسؤل على تعديل هيكل تقرير من خلال اضافة نقاط جديدة او مسح نقاط او تعديل عنوان معين او تعديل المحتوى الذس سيكتب في عنوان معين وكل التعديلات تكون في ظل الاحداث السياسية الاخيرة الحديثة
                          """
        },
        {"role": "user", "content":f" {article_json}خصص جميع التعديلات في ضوء القضية المتناولة في ذلك التقرير"},
        {"role": "user", "content": arabic_prompt},
        {"role": "user", "content": article_json}
    ]

    try:
        response = llm.chat.completions.create(
            model="gpt-4o",
            messages=conversation_history
        ).choices[0].message.content

        # Clean and parse the response
        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[len("```json"):].strip()
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3].strip()

        return cleaned_response
    except Exception as e:
        return {"error": str(e)}

# API route to update an Arabic article
@app.route('/update_article', methods=['POST'])
def update_article():
    """
    API endpoint to update an Arabic article based on user input.

    Request format:
        {
            "article_json": "<original JSON as string>",
            "arabic_prompt": "<editing prompt>"
        }

    Response format:
        {
            "updated_article": <updated JSON object>
        }
    """
    try:
        data = request.get_json()
        article_json = data.get('article_json', '')
        arabic_prompt = data.get('arabic_prompt', '')

        if not article_json or not arabic_prompt:
            return jsonify({"error": "Both 'article_json' and 'arabic_prompt' are required."}), 400

        updated_article = update_arabic_article(article_json, arabic_prompt)
        return updated_article, 200
    except Exception as e:
        updated_article = update_arabic_article(article_json, arabic_prompt)
        return updated_article, 200

# Root route for testing
@app.route('/')
def home():
    return "<p>Arabic Article Update API is running!</p>"

if __name__ == '__main__':
    app.run(debug=True)
