from flask import Flask, request, jsonify
import json
import requests
from bs4 import BeautifulSoup
from openai import AzureOpenAI
from flasgger import Swagger, swag_from
from flask_swagger_ui import get_swaggerui_blueprint
from flask_cors import CORS

# Initialize Azure OpenAI
llm = AzureOpenAI(
    azure_endpoint="https://genral-openai.openai.azure.com/",
    api_key="8929107a6a6b4f37b293a0fa0584ffc3",
    api_version="2024-02-01"
)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# Swagger UI setup
SWAGGER_URL = '/api/docs'
API_URL = '/static/swagger.json'

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={'app_name': "AutoML APIs"}
)
app.register_blueprint(swaggerui_blueprint)

swagger = Swagger(app, template={
    "info": {
        "title": "AutoML APIs",
        "description": "API for Automated Machine Learning tool",
        "version": "1.0.0"
    },
    "host": "https://generatereport-b3cxe2frencvekh5.eastus-01.azurewebsites.net",
    "basePath": "/",
})
def fetch_url_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        # Extract the main content (this may vary depending on the structure of the webpage)
        return soup.get_text(separator="\n", strip=True)
    except Exception as e:
        print(f"Error fetching content from {url}: {e}")
        return None
    
def fetch_urls(موضوع_التقرير, منظور_التقرير):
    """
    Fetch URLs based on موضوع التقرير and منظور التقرير using an external API.
    """
    try:
        api_endpoint = "https://ndc-bing-search-hrhra6fkcuaffjby.canadacentral-01.azurewebsites.net/bing_search"
        print(منظور_التقرير)
        print(موضوع_التقرير)
        payload = {
            "منظور_التقرير": منظور_التقرير,
            "موضوع_التقرير": موضوع_التقرير
        }
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }

        response = requests.post(api_endpoint, json=payload, headers=headers)
        response.raise_for_status()
        return response.json().get("URLs", [])
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def process_with_llm(content, query):
    try:
        conversation_history = [
            {"role": "system", "content": "You are an Arabic journalist tasked with enriching content for a report."},
            {"role": "user", "content": f"Here is the content from the webpage:\n\n{content}\n\n{query}"}
        ]
        response = llm.chat.completions.create(
            model="gpt-4o",
            messages=conversation_history
        ).choices[0].message.content
        return response
    except Exception as e:
        print(f"Error processing content with LLM: {e}")
        return None
    
def process_urls(urls, query):
    """
    Process a list of URLs and retrieve content summarized with a query.
    """
    results = []
    for url in urls:
        print(f"Fetching content from {url}...")
        content = fetch_url_content(url)
        if content:
            print(f"Processing content for {url}...")
            llm_response = process_with_llm(content, query)
            results.append({"url": url, "Article Content": llm_response})
        else:
            results.append({"url": url, "response": "Failed to fetch content."})
    return results

@app.route('/generate-arabic-report', methods=['POST'])
def edit_arabic_report():
    """
    API endpoint to edit an Arabic report JSON using GPT-4o with additional URL content enrichment.
    """
    try:
        data = request.get_json()
        json_input_string = data.get('json_input')
        arabic_prompt = data.get('Heading_name')

        if not json_input_string or not arabic_prompt:
            return jsonify({"error": "Both 'json_input' and 'Heading_name' are required."}), 400

        try:
            input_json = json.loads(json_input_string)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid JSON format in 'json_input'."}), 400

        # Extract topic and perspective from the input JSON
        headings = input_json.get("headings", [])
        prompt = f"""
    المقال الحالي يتحدث عن:
    {json.dumps(headings, ensure_ascii=False, indent=2)}

    استخرج موضوع المقال في جملة واحدة بناءً على النص، وحدد من واحد لثلاث نظر للتقرير كحد اقصى من الخيارات التالية: [سياسي, إقتصادي, إجتماعي, تكنولوجي, بيئي, ثقافي, علمي, قانوني]. قدم الإجابة كالتالي:
    موضوع التقرير= <العنوان>
    منظور التقرير= [<القيم الثلاث فقط>]
    إجتماعي ,منظور التقرير يجب ان يحتوي على واحدة من  [سياسي, إقتصادي, إجتماعي, تكنولوجي, بيئي, ثقافي, علمي, قانوني] دون تغيير ولا كلمة و لاحظ مكان الهمزة في بعض الكلمات مثل : إقتصادي

    """
        conversation_history = [
            {"role": "system", "content": "أنت مساعد متخصص في تحليل النصوص."},
            {"role": "user", "content": prompt}
        ]
        llm_response = llm.chat.completions.create(
            model="gpt-4o",
            messages=conversation_history
        ).choices[0].message.content

        topic = llm_response.split("موضوع التقرير=")[1].split("\n")[0].strip()
        perspective = llm_response.split("منظور التقرير=")[1].strip().strip("[]").split(",")
        perspective = [p.strip() for p in perspective]


        # Fetch URLs and content
        urls = fetch_urls(topic, perspective)
        url_contents = [fetch_url_content(url) for url in urls if fetch_url_content(url)]
        #urls = fetch_urls(topic, perspective)
        #query = "Without any summarization, Retrieve all the content of the webpage in Arabic."
        #results = process_urls(urls, query)
        print(url_contents)
        # Enrich prompt with URL contents
        enriched_prompt = arabic_prompt + "\n\n" + "يرجى تضمين إحصائيات وتحليلات مفصلة في كل نقطة فرعية لذلك heading، وشرح وافٍ و مفصل و كثيف بالمحتوى مع تقسيم heading إلى أكثر من عنوان فرعي. استخدم  كل البيانات و المصادر التالية دون اهمال احدهم من المصادر لدعم المحتوى:\n\n" + "\n\n".join(url_contents)
        conversation_history.append({
    "role": "system",
    "content": "You are a professional journalist tasked with writing a detailed informative and valuable Arabic article in JSON format. The output should contain detailed statistics and analysis for every point in a Specific heading as the input json will contain some headings and some points and your mission is to fill the content of each point in specific heading."
})

        conversation_history.append({
    "role": "user",
    "content": f"""
    قي نفس شكل ال JSON Formatبدون اي تغيير فيه, انا اريد الJson فقط بدون اي شروحات اضافية او في ال style قم بتحسين المقال التالي:\n{enriched_prompt}
قم بكتابة مقال كامل عن ذلك العنوان {arabic_prompt}
ذلك عن طريق كتابة محتوى لكل نقطة موجودة في ذلك{input_json} headingو تابعة لل{arabic_prompt} فلا تقوم بنقص احدى النقاط بل قم بكتابة محتوها جميعها
المحتوى يجب ان يكون مفصل و كثيف و بناء عن المصادر و يفضل اذا احتاج الامر مش شرط دائما ان كان هناك tables توضع و سضع تحتها مصدرها و عنوان عنها 
محتوى النقاط يجب ان يكتب ب HTML Tags
الoutput json يجب ان يحتوي فقط على ذلك ال {arabic_prompt} بعد كتابة التقرير المفصل
فيجب كتابة المحتوى ال content للنقاط الموجودة في listItemsList and listItems لذلك ال  {arabic_prompt} فقط
ال output يجب ان يكون في valid json
انا لا اريد كتابة كلام في ال content بين "" لكن اريد بين ()
يجب ان كل  content يحتوي من سبع لعشر فقرات كبار و طوال مليئين بالتفاصيل الغنية 
برهن ودلل على المحتوى في الـ content بالمعلومات المستندة إلى المصادر، مع استخدام إحصائيات وأرقام مستخرجة منها. يمكنك أن تشير إلى المصدر بقول "حسب ذلك المصدر" ثم تقدم البرهان المناسب.
لا تنسى ال tables اذا احتاج الامر في ال content
أنا اريد فقط في الاجابة ال JSON file بدون اي شروحات اضافية
قم بإرجاع JSON صالح فقط بدون أي نصوص إضافية أو شروحات. يجب أن يبدأ الرد بـ "{" وينتهي بـ "}".
يجب ان تكون الاجابة في شكل JSON
و ال output JSON headingيحمل التعديلات لذلك ال {arabic_prompt} 
فانا لا اريد المقال بheadings بل اريد ال heading المطلوب فقط
تاكد من كتابة ال HTML Tags بشكل صحيح
تاكد اني اريد فقط ال JSON File
تاكد اني اريد JSON صحيح بدون errors 
"""

})

        enriched_response = llm.chat.completions.create(
            model="gpt-4o",
            messages=conversation_history
        ).choices[0].message.content
        print("Raw API response:", enriched_response)


        # Parse the enriched GPT response
        cleaned_response = enriched_response.strip()
        if cleaned_response.startswith('```json'):
            cleaned_response = cleaned_response[len('```json'):].strip()
        if cleaned_response.endswith('```'):
            cleaned_response = cleaned_response[:-3].strip()

        try:
            updated_json = json.loads(cleaned_response)
        except json.JSONDecodeError:
            return jsonify({"error": "GPT response is not valid JSON."}), 500

        return jsonify({"updated_json": updated_json}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def hello_world():
    return "<p>Arabic Report Editor is running!</p>"

if __name__ == '__main__':
    app.run(debug=True)
