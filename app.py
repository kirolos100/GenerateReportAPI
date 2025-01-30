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

    استخرج موضوع المقال في جملة واحدة بناءً على النص، وحدد من واحد لاثنان نظر للتقرير كحد اقصى من الخيارات التالية: [سياسي, إقتصادي, إجتماعي, تكنولوجي, بيئي, ثقافي, علمي, قانوني]. قدم الإجابة كالتالي:
    موضوع التقرير= <العنوان>
    منظور التقرير= [<القيم الاثنان فقط>]
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
        
        if "موضوع التقرير=" not in llm_response or "منظور التقرير=" not in llm_response:
           
            prompt = f"""
                المقال الحالي يتحدث عن:
                {json.dumps(headings, ensure_ascii=False, indent=2)}

                استخرج موضوع المقال في جملة واحدة بناءً على النص  قدم الإجابة كالتالي:
                <العنوان>
                قدم الاجابة في جملة واحدة عنوان واحد فقط بدون شروحات او اضافات اخرى جملة واحدة فقط
                """
            conversation_history = [
                            {"role": "system", "content": "أنت مساعد متخصص في تحليل النصوص."},
                            {"role": "user", "content": prompt}
                        ]
            llm_response = llm.chat.completions.create(
                            model="gpt-4o",
                            messages=conversation_history
                        ).choices[0].message.content
            topic=llm_response
            perspective= ["غير_محدد"]

        else:

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
  "content": "You are a professional analyst and journalist with a keen ability to provide detailed informative, valuable,  predictive insights and detailed forecasting. Your task is to write a detailed Arabic article in JSON format, not as a string. The output should contain comprehensive statistics, predictive analysis, and future trends for each point under a specific heading. The input JSON will contain headings and key points, and your mission is to enhance each point with in-depth forecasts, valuable insights, and actionable recommendations under its respective heading."
})

        conversation_history.append({
    "role": "user",
    "content": f"""
    قي نفس شكل ال JSON Formatبدون اي تغيير فيه, انا اريد الJson فقط بدون اي شروحات اضافية او في ال style قم بتحسين المقال التالي:\n{enriched_prompt}
قم بكتابة مقال كامل عن ذلك العنوان {arabic_prompt}
ذلك عن طريق كتابة محتوى لكل نقطة موجودة في ذلك{input_json} headingو تابعة لل{arabic_prompt} فلا تقوم بنقص احدى النقاط بل قم بكتابة محتوها جميعها
المحتوى يجب ان يكون حديث و مفصل و كثيف و بناء عن المصادر و يفضل اذا احتاج الامر مش شرط دائما ان كان هناك tables توضع و سضع تحتها مصدرها و عنوان عنها 
محتوى النقاط يجب ان يكتب ب HTML Tags
الoutput json يجب ان يحتوي فقط على ذلك ال {arabic_prompt} بعد كتابة التقرير المفصل
فيجب كتابة المحتوى ال content للنقاط الموجودة في listItemsList and listItems لذلك ال  {arabic_prompt} فقط
ال output يجب ان يكون في valid json
انا لا اريد كتابة كلمة او مصطلح وسط المحتوى في ال content بين "" لكن اريد بين ()
يجب ان كل  content يحتوي من خمس لسبع فقرات كبار و طوال مليئين بالتفاصيل الغنية و الحديثة
برهن ودلل على المحتوى في الـ content بالمعلومات المستندة إلى المصادر، مع استخدام إحصائيات وأرقام مستخرجة منها. يمكنك أن تشير إلى المصدر بذكر اسم المصدر المستخدم فلا "حسب ذلك المصدر" فقط بل اذكر اسمه او عنوانه  و بيانات عنه مثل اسم الكاتب و عنوان المقال و اسم الموقع او الصحيفة اذا توفر اسمه فيكون ذلك لحفظ حقوق المصدر ثم تقدم البرهان المناسب.
لا تنسى ال tables اذا احتاج الامر في ال content
أنا اريد فقط في الاجابة ال JSON file بدون اي شروحات اضافية
قم بإرجاع JSON صالح فقط بدون أي نصوص إضافية أو شروحات. يجب أن يبدأ الرد بـ "{" وينتهي بـ "}".
يجب ان تكون الاجابة في شكل JSON فقط يتكون من :    
    **تفاصيل المحتوى المطلوب:**
    - يجب أن يحتوي كل "content" على 5-7 فقرات مفصلة وغنية بالتفاصيل.
    - احذر من الاخطاء الاملائية او من الجمل الناقصة
    - انا لا اريد كتابة كلمة او مصطلح وسط المحتوى في ال content بين "" لكن اريد بين ()
    - استخدم علامات HTML صحيحة ودقيقة (<p></p>، <table></table>، إلخ.).
    - إذا كان هناك حاجة لعرض جداول، قم بتضمينها مع ذكر مصدرها أسفل الجدول.
    - قدم المحتوى مدعومًا بالإحصائيات والمصادر الموثوقة (على سبيل المثال، "حسب ذلك المصدر").
    - لا تستخدم علامات الاقتباس ("") داخل محتوى الفقرات، واستخدم الأقواس العادية () عند الحاجة.
    - تأكد من تصحيح الأخطاء الإملائية وأي مشاكل في التنسيق (مثل </p>>).
    - لا تنسى ال tables اذا احتاج الامر في ال content
    - في ال content اذكر الخطوات و القرارات التي ستتخذها تلك الجهة السيادية المستهدفة من التقرير في شكل نقاط
    - لا تنسى ان تزيد دائما توقعاتك و تنبؤاتك و رايك في ال content لكل نقطة مزودة بالارقام و التواريخ الحديثة في ظل الاحداث الاخيرة و الاحصائيات
    - توقعاتك يجب ان تكون فيها رأي مبرهن بالمصادر مع تواريخ الحديثة في ظل الاحداث الاخيرة و ارقام و احصائيات و قل انها المتوقعة 
    - دائما اذكر رأيك و لا تتكلم بشكل عام بل تكلم اكثر بشكل أخص
    **الإجابة المطلوبة:**
    - أريد ملف JSON صالحًا فقط يبدأ بـ "{" وينتهي بـ "}".
    - لا أريد أي شروحات أو نصوص إضافية في الإجابة.
    - قم بإرجاع المحتوى وفق الصيغة المطلوبة فقط.

    تأكد أن ملف JSON الناتج:
    - يحتوي على الحقول "headings" و"listItemsList" و"listItems" مكتملة وصحيحة.
    - متناسق وصالح للاستخدام بدون أي أخطاء في التنسيق.
    - يبدأ وينتهي بـ "{" و"}".
    
                  
ال headings  المفروض انها one only array of objects
يجب ان الheadings تحتوي على list كبيرة التي تحتوي على listItmesList list & listItems list
و ال output JSON headingيحمل التعديلات لذلك ال {arabic_prompt} 
لا تنسى ال title: {arabic_prompt} ولا تنسى ال version : 1
فانا لا اريد المقال بheadings بل اريد ال heading المطلوب فقط
تاكد من كتابة ال HTML Tags بشكل صحيح
لا تنسى ال tables اذا احتاج الامر علو الاقل في نقطة واحدة في ال content
تاكد اني اريد فقط ال JSON File بدون اي اضافات او شروحات
تاكد اني اريد JSON صحيح بدون errors: 
قم بتصحيح العلامة </p>> غير المتطابقة إلى </p> 
إزالة المسافات الزائدة وإصلاح الأخطاء الإملائية في جميع الأقسام.
تأكد من تنسيق كافة العلامات بشكل صحيح.
أكمل محتوى لاي من النقاط أو قم بإزالة الجزء الناقص.
قم بارجاع الناتج النهائي في شكل JSON Format و احذر ان ترجع ب String Format
قم بإرجاع JSON صالح فقط بدون أي نصوص إضافية أو شروحات. يجب أن يبدأ الرد بـ "{" وينتهي بـ "}".
توقعاتك يجب ان تكون فيها رأي مبرهن بالمصادر مع تواريخ الحديثة في ظل الاحداث الاخيرة و ارقام و احصائيات و قل انها المتوقعة 
برهن ودلل على المحتوى في الـ content بالمعلومات المستندة إلى المصادر، مع استخدام إحصائيات وأرقام مستخرجة منها. يمكنك أن تشير إلى المصدر بذكر اسم المصدر المستخدم فلا "حسب ذلك المصدر" فقط بل اذكر اسمه او عنوانه  و بيانات عنه مثل اسم الكاتب و عنوان المقال و اسم الموقع او الصحيفة اذا توفر اسمه فيكون ذلك لحفظ حقوق المصدر ثم تقدم البرهان المناسب.
 دائما اذكر رأيك مع امثلة هامة و مصطلحات سياسية مهمة تجعل من رأيك رأي مهم للعمل به و برهن على رايك من المصادر و لا تتكلم بشكل عام بل تكلم اكثر بشكل أخص
لا تنسى ان تزيد دائما توقعاتك و تنبؤاتك و رايك في ال content لكل نقطة مزودة بالارقام و التواريخ الحديثة في ظل الاحداث الاخيرة و الاحصائيات
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
        cleaned_response = cleaned_response.replace('`', '').strip()
        return cleaned_response , 200
    except Exception as e:
        edit_arabic_report()
        return jsonify({"error": str(e)}), 500

@app.route("/")
def hello_world():
    return "<p>Arabic Report Editor is running!</p>"

if __name__ == '__main__':
    app.run(debug=True)
