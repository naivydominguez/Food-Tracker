import base64
from openai import OpenAI

client = OpenAI()

with open("food.jpg", "rb") as f:
    image_data = base64.b64encode(f.read()).decode("utf-8") #convert into a text string to send via api

prompt = """Analyze this food image and respond in exactly this format:

FOOD IDENTIFIED: [name of the food]

CALORIES:
- Total estimate: [X] calories per serving
- Serving size: [estimated serving size]
- Breakdown (if multiple items): [item: X cal, item: X cal, ...]

RECIPES USING THIS FOOD:
1. [Recipe Name]
   - Brief description (1-2 sentences)
   - Key ingredients: [list]
   - Cook time: [X mins]

2. [Recipe Name]
   - Brief description (1-2 sentences)
   - Key ingredients: [list]
   - Cook time: [X mins]

3. [Recipe Name]
   - Brief description (1-2 sentences)
   - Key ingredients: [list]
   - Cook time: [X mins]"""

response = client.responses.create(
    model="gpt-5.5",
    input=[
        {
            "role": "user",
            "content": [
                {
                    "type": "input_image",
                    "image_url": f"data:image/jpeg;base64,{image_data}"
                },
                {
                    "type": "input_text",
                    "text": prompt
                }
            ]
        }
    ]
)

print(response.output_text)

