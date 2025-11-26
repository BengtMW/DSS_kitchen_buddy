import webbrowser
import uvicorn

# Open default browser at http://localhost:8000
webbrowser.open("http://localhost:8000")

# Run FastAPI backend
if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",  # module:path
        host="127.0.0.1",
        port=8000,
        reload=True
    )