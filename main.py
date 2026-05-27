# def main():
#     print("Hello from test-claiudesdk!")


# if __name__ == "__main__":
#     main()


import shutil
from fastapi import FastAPI, UploadFile
from fastapi.responses import HTMLResponse
from pathlib import Path
import shutil


app = FastAPI()
DIR = Path('/run/media/bhat/workspace/projects/test_claiudesdk')
DIR.mkdir(exist_ok=True)
# ALLOWED_MIMETYPES = mimetypes.common_types('.pdf')

@app.get("/", response_class=HTMLResponse)
async def main_page():
    content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>File Upload</title>
        <style>
            body { font-family: sans-serif; margin: 50px; }
            .container { max-width: 400px; padding: 20px; border: 1px solid #ccc; }
            button { margin-top: 10px; padding: 5px 15px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Upload Your File</h2>
            <form action="/upload" method="post" enctype="multipart/form-data">
                <input type="file" name="file" required>
                <br>
                <button type="submit">Upload</button>
            </form>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=content)


@app.post('/upload')
async def upload_file(file: UploadFile):
    if not file:
        return ("No file uploaded")
    if file:

        des = DIR / file.filename

        with des.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            print(f'file saved sucessfully {file.filename}')

        return {'Upload Sucessful': f"Saved to {des}"}

