import os
import sys
import threading
import time
import urllib.request
import webbrowser
import uvicorn


def open_when_ready(port):
    for _ in range(100):
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health',timeout=1) as response:
                if response.status==200:
                    webbrowser.open(f'http://127.0.0.1:{port}/home'); return
        except Exception:
            time.sleep(.2)


if __name__=='__main__':
    port=int(os.environ.get('VIXISU_PORT','8000'))
    if '--open' in sys.argv:
        threading.Thread(target=open_when_ready,args=(port,),daemon=True).start()
    uvicorn.run('app.main:app',host='127.0.0.1',port=port,reload=False)
