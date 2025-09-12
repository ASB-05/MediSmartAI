import pandas as pd
from sklearn.linear_model import LogisticRegression
import os
import json
from openai import OpenAI, AuthenticationError, RateLimitError, APIConnectionError, APIStatusError

# This will be our custom client for OpenRouter
client = None
IS_AI_CONFIGURED = False

def initialize_ai_client():
    """Initializes the AI client with the OpenRouter API key and base URL."""
    global client, IS_AI_CONFIGURED
    
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("\n\n!!! WARNING: OPENROUTER_API_KEY not found. AI features will be disabled. !!!\n\n")
        IS_AI_CONFIGURED = False
        return

    client = OpenAI(
      base_url="https://openrouter.ai/api/v1",
      api_key=api_key,
      default_headers={
          "HTTP-Referer": "http://localhost:5000", 
          "X-Title": "MediSmart AI",
      },
    )
    IS_AI_CONFIGURED = True
    print("--- OpenRouter AI Client Initialized ---")

initialize_ai_client()

# --- AI Model 1: Schedule Optimizer (Scikit-learn) ---
# This local model does not need to change.
scheduler_data = {
    'hour': [9, 10, 11, 12, 13, 14, 15, 16, 9.5, 10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 16.5],
    'is_booked': [1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0],
    'is_optimal': [1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1]
}
scheduler_df = pd.DataFrame(scheduler_data)
X_scheduler = scheduler_df[['hour', 'is_booked']]
y_scheduler = scheduler_df['is_optimal']
scheduler_model = LogisticRegression()
scheduler_model.fit(X_scheduler, y_scheduler)

def get_schedule_suggestions(doctor_name, selected_date, appointments_collection):
    """Provides scikit-learn driven time slot suggestions."""
    time_slots = [f"{h:02d}:{m:02d}" for h in range(9, 17) for m in (0, 30)]
    booked_slots = {app['time'] for app in appointments_collection.find({'doctorName': doctor_name, 'date': selected_date})}
    suggestions = []
    for slot in time_slots:
        if slot in booked_slots:
            continue
        hour = int(slot.split(':')[0]) + (0.5 if slot.endswith(':30') else 0)
        prediction_data = pd.DataFrame({'hour': [hour], 'is_booked': [0]})
        prediction = scheduler_model.predict(prediction_data)[0]
        status = 'optimal' if prediction == 1 else 'busy'
        suggestions.append({'time': slot, 'status': status})
    return suggestions


# --- AI Model 2: Symptom Checker (OpenRouter) ---
def get_symptom_recommendation_openai(symptoms):
    """Provides a specialist recommendation based on symptoms using OpenRouter."""
    if not IS_AI_CONFIGURED:
        return {'recommendation': "a General Physician (AI service not configured)."}
    
    prompt = f'A user has described their symptoms as: "{symptoms}". Based on these symptoms, what is the most likely medical specialist they should see? Please provide only the specialist name, for example: "Cardiologist".'
    
    try:
        response = client.chat.completions.create(
            model="mistralai/mistral-7b-instruct:free",
            messages=[
                {"role": "system", "content": "You are a helpful medical assistant. Respond with only the name of a single medical specialty."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1, max_tokens=50
        )
        # ** THE FIX IS HERE: Directly use the text response **
        recommendation_text = response.choices[0].message.content
        return {'recommendation': f"a {recommendation_text}"}
    except Exception as e:
        print(f"OpenRouter Error (Symptom Checker): {e}")
        return {'recommendation': "Could not get a recommendation due to an API error."}


# --- AI Model 3: NutriAI Diet Planner (OpenRouter) ---
def get_diet_recommendation_openai(disease, user_details):
    """Generates a diet recommendation using OpenRouter."""
    if not IS_AI_CONFIGURED:
        return {'diet': "A general balanced diet (AI service not configured)."}

    prompt = f"Generate a concise diet recommendation in a single paragraph for a patient with {disease} and the following notes: {user_details}"
    
    try:
        response = client.chat.completions.create(
            model="mistralai/mistral-7b-instruct:free",
            messages=[
                {"role": "system", "content": "You are an expert AI nutritionist. Respond with a single paragraph outlining a diet plan."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5, max_tokens=300
        )
        # ** THE FIX IS HERE: We no longer need to parse JSON. We just use the text directly. **
        result_text = response.choices[0].message.content
        return {'diet': result_text}
    
    except AuthenticationError:
        error_message = "Authentication Error: Your OpenRouter API key is invalid. Please check your .env file."
        return {'diet': error_message}
    except RateLimitError:
        error_message = "Rate Limit Error: You have exceeded your OpenRouter quota. Please check your account usage."
        return {'diet': error_message}
    except Exception as e:
        error_message = "An unexpected error occurred. Please check the server logs."
        print(f"OpenRouter Error (NutriAI): An unexpected error occurred -> {e}")
        return {'diet': error_message}