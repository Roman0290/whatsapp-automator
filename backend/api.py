# api.py
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from werkzeug.utils import secure_filename
import os
from driver import Bot

app = FastAPI()

origins = [
    "http://localhost:5500",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.post("/login")
async def login(prefix: str = Form(...)):
    if not prefix:
        raise HTTPException(status_code=400, detail="Missing phone prefix")

    # Your login initiation logic here (e.g., setting up the bot)
    global bot_instance
    try:
        bot_instance = Bot()
        bot_instance.login(prefix, send_to_contacts=False, send_to_groups=False)
        return JSONResponse(content={"message": "Login initiated. Please scan the QR code."})
    except Exception as e:
        print(f"Error during login initiation: {e}")
        raise HTTPException(status_code=500, detail=f'Error initiating login: {str(e)}')

@app.post("/login_and_send")
async def login_and_send(
    prefix: str = Form(...),
    messageFile: UploadFile = File(...),
    numbersFile: UploadFile = File(...),
    includeNames: str | None = Form(None)
):
    if not prefix or not messageFile or not numbersFile:
        raise HTTPException(status_code=400, detail="Missing required fields")

    include_names = includeNames == 'true'

    try:
        message_file_path = os.path.join(UPLOAD_FOLDER, secure_filename(messageFile.filename))
        numbers_file_path = os.path.join(UPLOAD_FOLDER, secure_filename(numbersFile.filename))

        with open(message_file_path, "wb") as buffer:
            buffer.write(await messageFile.read())
        with open(numbers_file_path, "wb") as buffer:
            buffer.write(await numbersFile.read())

        bot = Bot()
        bot.csv_numbers = numbers_file_path
        bot.message = message_file_path
        bot.options = [include_names, False]

        print(f"Starting login with prefix: {prefix}")
        bot.login(prefix, send_to_contacts=True, send_to_groups=False)
        print("Login successful. Sending messages...")
        bot.send_messages_to_all_contacts()
        print("Message sending process completed.")

        return JSONResponse(content={'message': 'Login and message sending process initiated successfully.'})

    except Exception as e:
        print(f"Error during login and sending: {e}")
        raise HTTPException(status_code=500, detail=f'An error occurred: {str(e)}')
    finally:
        # Clean up uploaded files if needed
        if os.path.exists(message_file_path):
            os.remove(message_file_path)
        if os.path.exists(numbers_file_path):
            os.remove(numbers_file_path)
        pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)