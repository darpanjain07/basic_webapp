from fastapi import FastAPI, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import csv
from uuid import uuid4

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# Predefined questions and options with associated scores
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

# Temporary storage for responses
responses = {}
csv_file_path = "responses.csv"

# Ensure CSV has the correct headers upon server start
def initialize_csv():
    with open(csv_file_path, "a", newline='') as file:
        writer = csv.writer(file)
        # Check if file is empty to write headers
        if file.tell() == 0:
            headers = ["email_id"] + [f"question{i+1}" for i in range(len(questions))] + ["total_score", "interpretation"]
            writer.writerow(headers)

initialize_csv()

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

@app.post("/submit_email")
async def submit_email(email: str = Form(...)):
    session_id = responses.get('current_session_id')
    if session_id:
        total_score = sum(responses[session_id]['scores'])
        if total_score < 8:
            interpretation = "It is unlikely that you are abnormally sleepy."
        elif total_score < 10:
            interpretation = "You have an average amount of daytime sleepiness."
        elif total_score < 16:
            interpretation = "You may be excessively sleepy depending on the situation. You may want to consider seeking medical attention."
        else:
            interpretation = "You are excessively sleepy and should consider seeking medical attention."
        
        with open(csv_file_path, "a", newline='') as file:
            writer = csv.writer(file)
            row = [email, *responses[session_id]['scores'], total_score, interpretation]
            writer.writerow(row)
        
        del responses[session_id]
        del responses['current_session_id']
        
        return {"email": email, "total_score": total_score, "interpretation": interpretation}

if __name__ == "__main__":
    import uvicorn
    host = "0.0.0.0"
    port = int(os.getenv("PORT", 8000))  # Default to 8000 if no PORT env var is set
    uvicorn.run("main:app", host=host, port=port, reload=True)