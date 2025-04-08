from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import json
import time
import logging
from typing import Optional
from driver import Bot

app = FastAPI(title="WhatsApp Automation API", version="1.0.0")

origins = [
    "http://localhost",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
     expose_headers=["*"],
)

UPLOAD_FOLDER = 'uploads'
LOG_FOLDER = 'logs'
ANALYTICS_REFRESH_INTERVAL = 300

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(LOG_FOLDER, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_FOLDER, 'api.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MessageRequest:
    def __init__(self, **kwargs):
        self.prefix = kwargs.get('prefix')
        self.message_type = kwargs.get('messageType')
        self.send_to_contacts = kwargs.get('sendToContacts', False)
        self.send_to_groups = kwargs.get('sendToGroups', False)
        self.include_names = kwargs.get('includeNames', False)
        self.file_paths = {}

@app.post("/login_and_send")
async def login_and_send(
    prefix: str = Form(...),
    messageType: str = Form(...),
    sendToContacts: bool = Form(False),
    sendToGroups: bool = Form(False),
    includeNames: bool = Form(False),
    numbersFile: Optional[UploadFile] = File(None),
    groupsFile: Optional[UploadFile] = File(None),
    messageFile: Optional[UploadFile] = File(None),
    mediaFile: Optional[UploadFile] = File(None),
    captionFile: Optional[UploadFile] = File(None)
):
    try:
        if not prefix:
            raise HTTPException(status_code=400, detail="Missing phone prefix")
        
        if not sendToContacts and not sendToGroups:
            raise HTTPException(status_code=400, detail="Must select at least one destination")

        if messageType not in ['text', 'media']:
            raise HTTPException(status_code=400, detail="Invalid message type")

        request = MessageRequest(
            prefix=prefix,
            messageType=messageType,
            sendToContacts=sendToContacts,
            sendToGroups=sendToGroups,
            includeNames=includeNames
        )

        request.file_paths = await save_uploaded_files(
            sendToContacts=sendToContacts,
            sendToGroups=sendToGroups,
            messageType=messageType,
            numbersFile=numbersFile,
            groupsFile=groupsFile,
            messageFile=messageFile,
            mediaFile=mediaFile,
            captionFile=captionFile
        )

        bot = Bot()
        await configure_bot(bot, request)

        results = await execute_messaging_campaign(bot, request)

        return JSONResponse(content={
            'status': 'success',
            'message': 'Messages sent successfully!',
            'results': results,
            'timestamp': datetime.now().isoformat()
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in login_and_send: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f'An error occurred: {str(e)}')
    finally:
        await cleanup_resources(request.file_paths)

async def save_uploaded_files(**kwargs) -> dict:
    file_paths = {}
    
    try:
        if kwargs.get('sendToContacts') and kwargs.get('numbersFile'):
            file_paths['numbers'] = await save_file(kwargs['numbersFile'])
        
        if kwargs.get('sendToGroups') and kwargs.get('groupsFile'):
            file_paths['groups'] = await save_file(kwargs['groupsFile'])
        
        if kwargs.get('messageType') == 'text' and kwargs.get('messageFile'):
            file_paths['message'] = await save_file(kwargs['messageFile'])
        elif kwargs.get('messageType') == 'media' and kwargs.get('mediaFile'):
            file_paths['media'] = await save_file(kwargs['mediaFile'])
            if kwargs.get('captionFile'):
                file_paths['caption'] = await save_file(kwargs['captionFile'])
    
    except Exception as e:
        logger.error(f"Error saving files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded files: {str(e)}")
    
    return file_paths

async def save_file(upload_file: UploadFile) -> str:
    if not upload_file:
        return None
        
    file_path = os.path.join(UPLOAD_FOLDER, secure_filename(upload_file.filename))
    with open(file_path, "wb") as buffer:
        buffer.write(await upload_file.read())
    return file_path

async def configure_bot(bot: Bot, request: MessageRequest):
    try:
        if request.send_to_contacts and 'numbers' in request.file_paths:
            bot.csv_numbers = request.file_paths['numbers']
        
        if request.send_to_groups and 'groups' in request.file_paths:
            bot.csv_groups = request.file_paths['groups']
        
        if request.message_type == 'text' and 'message' in request.file_paths:
            bot.message = request.file_paths['message']
        elif request.message_type == 'media' and 'media' in request.file_paths:
            bot.media = request.file_paths['media']
            if 'caption' in request.file_paths:
                with open(request.file_paths['caption'], 'r') as f:
                    bot.message = f.read()
        
        bot.options = [request.include_names, request.send_to_groups]
    
    except Exception as e:
        logger.error(f"Error configuring bot: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Bot configuration failed: {str(e)}")

async def execute_messaging_campaign(bot: Bot, request: MessageRequest) -> dict:
    results = {
        'contacts': {'success': 0, 'failed': 0},
        'groups': {'success': 0, 'failed': 0}
    }
    
    try:
        logger.info(f"Starting login with prefix: {request.prefix}")
        bot.login(
            request.prefix,
            send_to_contacts=request.send_to_contacts,
            send_to_groups=request.send_to_groups
        )
        logger.info("Login successful. Sending messages...")
        
        if request.message_type == 'text':
            if request.send_to_contacts:
                results['contacts'] = bot.send_messages_to_all_contacts()
            if request.send_to_groups:
                results['groups'] = bot.send_messages_to_all_groups()
        else:
            if request.send_to_contacts:
                results['contacts'] = bot.send_media_to_all_contacts()
            if request.send_to_groups:
                results['groups'] = bot.send_media_to_all_groups()
        
        logger.info("Message sending process completed.")
        return results
    
    except Exception as e:
        logger.error(f"Error executing campaign: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Message sending failed: {str(e)}")

async def cleanup_resources(file_paths: dict):
    for file_path in file_paths.values():
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.warning(f"Failed to delete file {file_path}: {str(e)}")

@app.get("/message_analytics")
async def get_message_analytics():
    try:
        if not os.path.exists(LOG_FOLDER):
            return JSONResponse(content={
                "status": "success",
                "summary": {"read": 0, "delivered": 0, "failed": 0, "sent": 0},
                "messages": [],
                "last_updated": datetime.now().isoformat()
            })

        messages = []
        summary = {"read": 0, "delivered": 0, "failed": 0, "sent": 0}

        for filename in os.listdir(LOG_FOLDER):
            filepath = os.path.join(LOG_FOLDER, filename)
            
            
            if filename.endswith('_detailed.json'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            status = data.get("status", "").lower()
                            
                            
                            if "read" in status:
                                status = "read"
                            elif "delivered" in status:
                                status = "delivered"
                            elif "sent" in status:
                                status = "sent"
                            elif "fail" in status:
                                status = "failed"
                            else:
                                status = "unknown"
                            
                            if status in summary:
                                summary[status] += 1
                            
                            messages.append({
                                "contact": data.get("contact", "Unknown"),
                                "message": data.get("message", ""),
                                "status": status,
                                "timestamp": data.get("timestamp", datetime.now().isoformat())
                            })
                        except json.JSONDecodeError:
                            continue
            
           
            elif filename.endswith('_sent.txt'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            messages.append({
                                "contact": line.strip(),
                                "message": "",
                                "status": "delivered",
                                "timestamp": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
                            })
                            summary["delivered"] += 1
            
            elif filename.endswith('_notsent.txt'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            messages.append({
                                "contact": line.strip(),
                                "message": "",
                                "status": "failed",
                                "timestamp": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
                            })
                            summary["failed"] += 1

        
        messages_sorted = sorted(
            messages,
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )[:200]  

        return JSONResponse(content={
            "status": "success",
            "summary": summary,
            "messages": messages_sorted,
            "last_updated": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error in analytics: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e),
                "summary": {"read": 0, "delivered": 0, "failed": 0, "sent": 0},
                "messages": []
            }
        )
async def generate_analytics_data() -> dict:
    try:
        log_files = [
            f for f in os.listdir(LOG_FOLDER)
            if f.endswith((".txt", ".json"))
        ]
        
        messages = []
        summary = {"read": 0, "delivered": 0, "failed": 0}
        
        for log_file in log_files:
            with open(os.path.join(LOG_FOLDER, log_file), "r") as f:
                if log_file.endswith(".json"):
                    for line in f:
                        try:
                            data = json.loads(line)
                            status = data.get("status", "unknown")
                            summary[status] += 1
                            messages.append({
                                "contact": data.get("number", "Unknown"),
                                "message": data.get("message", ""),
                                "status": status,
                                "timestamp": data.get("timestamp", datetime.now().isoformat())
                            })
                        except json.JSONDecodeError:
                            continue
                else:
                    for line in f:
                        status = "read" if "sent" in log_file else "failed"
                        summary[status] += 1
                        messages.append({
                            "contact": line.strip(),
                            "message": "",
                            "status": status,
                            "timestamp": datetime.now().isoformat()
                        })
        
        return {
            "status": "success",
            "summary": summary,
            "messages": sorted(messages, key=lambda x: x["timestamp"], reverse=True)[:100],
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error processing log files: {str(e)}")
        raise

@app.get("/dashboard")
async def serve_dashboard():
    try:
        with open("frontend/dashboard.html", "r") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Dashboard not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)