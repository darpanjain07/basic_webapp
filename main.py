from fastapi import FastAPI, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import csv
from uuid import uuid4
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import json
from dotenv import load_dotenv

load_dotenv()


creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
if creds_json is None:
    raise ValueError("Missing GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable")

# Load credentials from json
creds_dict = json.loads(creds_json)
creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
SPREADSHEET_ID = "1ovBjlk7I-l5rv87pIbKZCFjhmAeODxee_6nCCKSlkl8"

service = build('sheets', 'v4', credentials=creds)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

questions = [
    {"question": "Sitting and reading", "options": ["No chance of dozing", "Slight chance of dozing", "Moderate chance of dozing", "High chance of dozing"]},
    {"question": "Watching TV", "options": ["No chance of dozing", "Slight chance of dozing", "Moderate chance of dozing", "High chance of dozing"]},
    {"question": "Sitting inactive in a public place (e.g., a theater or a meeting)", "options": ["No chance of dozing", "Slight chance of dozing", "Moderate chance of dozing", "High chance of dozing"]},
    {"question": "As a passenger in a car for an hour without a break", "options": ["No chance of dozing", "Slight chance of dozing", "Moderate chance of dozing", "High chance of dozing"]},
    {"question": "Lying down to rest in the afternoon when circumstances permit", "options": ["No chance of dozing", "Slight chance of dozing", "Moderate chance of dozing", "High chance of dozing"]},
    {"question": "Sitting and talking to someone", "options": ["No chance of dozing", "Slight chance of dozing", "Moderate chance of dozing", "High chance of dozing"]},
    {"question": "Sitting quietly after a lunch without alcohol", "options": ["No chance of dozing", "Slight chance of dozing", "Moderate chance of dozing", "High chance of dozing"]},
    {"question": "In a car, while stopped for a few minutes in traffic", "options": ["No chance of dozing", "Slight chance of dozing", "Moderate chance of dozing", "High chance of dozing"]}
]

responses = {}
csv_file_path = "responses.csv"

def write_to_sheet(data):
    # Example: Append the data to the sheet
    sheet = service.spreadsheets()
    body = {
        'values': [data]
    }
    result = sheet.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range="Sheet1",  # Change if your sheet's name is different
        valueInputOption="USER_ENTERED",
        body=body
    ).execute()
    print(f"{result.get('updates').get('updatedCells')} cells appended.")

@app.get("/")
async def root():
    return FileResponse('static/index.html')

@app.get("/questions/{question_id}")
async def get_question(question_id: int):
    if question_id < 1 or question_id > len(questions):
        raise HTTPException(status_code=404, detail="Question not found")
    return questions[question_id - 1]

@app.post("/submit/{question_id}")
async def submit_response(question_id: int, choice: str = Form(...)):
    if question_id < 1 or question_id > len(questions):
        raise HTTPException(status_code=404, detail="Question not found")
    
    session_id = responses.get('current_session_id')
    if not session_id:
        session_id = uuid4().hex
        responses['current_session_id'] = session_id
        responses[session_id] = {'scores': []}
    
    # Map choice to score based on the position in the options list
    score_map = {option: idx for idx, option in enumerate(questions[question_id - 1]['options'])}
    score = score_map[choice]
    responses[session_id]['scores'].append(score)
    
    return {"question_id": question_id, "selected_option": choice, "score": score}

@app.post("/submit_phone")
async def submit_phone(phone: str = Form(...)):
    if not phone.isdigit() or len(phone) != 10:
        raise HTTPException(status_code=400, detail="Invalid phone number. It must be exactly 10 digits.")
    
    session_id = responses.get('current_session_id')
    if session_id:
        total_score = sum(responses[session_id]['scores'])
        if total_score < 8:
            interpretation = "It is unlikely that you are abnormally sleepy."
            risk_level_short = "nil_risk"
        elif total_score < 10:
            interpretation = "You have an average amount of daytime sleepiness."
            risk_level_short = "low_risk"
        elif total_score < 16:
            interpretation = "You may be excessively sleepy depending on the situation. You may want to consider seeking medical attention."
            risk_level_short = "moderate_risk"
        else:
            interpretation = "You are excessively sleepy and should consider seeking medical attention."
            risk_level_short = "high_risk"
        
        data_row = [phone, *responses[session_id]['scores'], total_score, interpretation, risk_level_short]
        write_to_sheet(data_row)
        
        # Clean up local response data
        del responses[session_id]
        del responses['current_session_id']
        
        return {"phone": phone, "total_score": total_score, "interpretation": interpretation, "risk_level_short": risk_level_short}

if __name__ == "__main__":
    import uvicorn
    host = "0.0.0.0"
    port = int(os.getenv("PORT", 8000))  # Default to 8000 if no PORT env var is set
    uvicorn.run("main:app", host=host, port=port, reload=True)