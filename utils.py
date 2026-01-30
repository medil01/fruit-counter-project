import os
from werkzeug.utils import secure_filename
from datetime import datetime

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}

def allowed_file(filename):
    """Проверка допустимого расширения файла"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file, upload_folder):
    """Сохранение загруженного файла"""
    if file and allowed_file(file.filename):
        # Создаем уникальное имя файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = secure_filename(f"{timestamp}_{file.filename}")
        filepath = os.path.join(upload_folder, filename)
        
        # Сохраняем файл
        file.save(filepath)
        return filepath
    
    return None

def cleanup_old_files(folder, max_age_hours=24):
    """Очистка старых файлов"""
    if not os.path.exists(folder):
        return
    
    current_time = datetime.now().timestamp()
    
    for filename in os.listdir(folder):
        filepath = os.path.join(folder, filename)
        if os.path.isfile(filepath):
            file_age = current_time - os.path.getmtime(filepath)
            if file_age > max_age_hours * 3600:  # Конвертируем часы в секунды
                try:
                    os.remove(filepath)
                except:
                    pass

def format_statistics(statistics):
    """Форматирование статистики для отображения"""
    if not statistics:
        return None
    
    formatted = {
        'total': statistics['total_fruits'],
        'by_fruit': statistics['fruit_counts'],
        'detections': len(statistics.get('detections', [])),
        'result_image': statistics.get('result_image', '')
    }
    
    return formatted
