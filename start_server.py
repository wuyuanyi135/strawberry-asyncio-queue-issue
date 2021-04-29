import uvicorn
from server import app
uvicorn.run(app, debug=True)