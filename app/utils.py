import os
from werkzeug.utils import secure_filename
from . import app

def save_file(file, folder):
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], folder, filename)
        file.save(file_path)
        return filename
    return None