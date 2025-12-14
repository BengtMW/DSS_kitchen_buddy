import webbrowser
import uvicorn
import time
import threading

def open_browser():
    time.sleep(1)  # attende che il server sia pronto
    webbrowser.open("http://127.0.0.1:8000")

threading.Thread(target=open_browser).start()

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",  # modulo:path
        host="127.0.0.1",
        port=8000,
        reload=True
    )