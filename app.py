from flask import Flask, render_template, request, jsonify, send_file, url_for
from flask_cors import CORS
import os
import time
from datetime import datetime

from fruit_detector import FruitDetector
from database import DatabaseManager
from report_generator import ReportGenerator
from utils import save_uploaded_file, cleanup_old_files, format_statistics

# Инициализация Flask приложения
app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max file size

# Создаем необходимые директории
UPLOAD_FOLDER = 'static/uploads'
RESULT_FOLDER = 'static/results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

# Инициализация компонентов
detector = FruitDetector()
db_manager = DatabaseManager()
report_gen = ReportGenerator(RESULT_FOLDER)

@app.route('/')
def index():
    """Главная страница"""
    # Получаем историю запросов
    history = db_manager.get_all_requests()[:10]  # Последние 10 запросов
    
    # Получаем ежедневную статистику
    daily_stats = db_manager.get_daily_statistics()
    
    return render_template('index.html', 
                         history=history, 
                         daily_stats=daily_stats)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Обработка загрузки изображения"""
    try:
        # Проверяем наличие файла
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Сохраняем файл
        filepath = save_uploaded_file(file, UPLOAD_FOLDER)
        if not filepath:
            return jsonify({'error': 'Invalid file type'}), 400
        
        # Засекаем время обработки
        start_time = time.time()
        
        # Детекция фруктов
        statistics = detector.detect_fruits(filepath)
        
        if not statistics:
            return jsonify({'error': 'Failed to process image'}), 500
        
        processing_time = time.time() - start_time
        
        # Сохраняем запрос в базу данных
        db_manager.save_request(
            filename=os.path.basename(filepath),
            statistics=statistics,
            processing_time=processing_time
        )
        
        # Форматируем результат
        result = format_statistics(statistics)
        result['processing_time'] = round(processing_time, 2)
        result['result_url'] = url_for('static', 
                                     filename=f'results/{os.path.basename(statistics["result_image"])}')
        
        # Очищаем старые файлы
        cleanup_old_files(UPLOAD_FOLDER)
        cleanup_old_files(RESULT_FOLDER)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error processing upload: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/history', methods=['GET'])
def get_history():
    """Получение истории запросов"""
    try:
        history = db_manager.get_all_requests()
        return jsonify(history)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/generate_report', methods=['POST'])
def generate_report():
    """Генерация отчета"""
    try:
        data = request.json
        report_type = data.get('type', 'pdf')
        
        # Получаем последний запрос для отчета
        history = db_manager.get_all_requests()
        if not history:
            return jsonify({'error': 'No data available for report'}), 400
        
        latest_request = history[0]
        
        # Генерируем отчет
        if report_type == 'pdf':
            report_path = report_gen.generate_pdf_report(
                statistics={
                    'total_fruits': latest_request['total_fruits'],
                    'fruit_counts': latest_request['fruit_counts']
                },
                request_data=latest_request
            )
        elif report_type == 'excel':
            report_path = report_gen.generate_excel_report(
                statistics={
                    'total_fruits': latest_request['total_fruits'],
                    'fruit_counts': latest_request['fruit_counts']
                },
                request_data=latest_request
            )
        else:
            return jsonify({'error': 'Invalid report type'}), 400
        
        # Возвращаем путь к отчету
        return jsonify({
            'report_url': url_for('static', 
                                filename=f'results/{os.path.basename(report_path)}'),
            'filename': os.path.basename(report_path)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/generate_history_report', methods=['GET'])
def generate_history_report():
    """Генерация отчета по всей истории"""
    try:
        history = db_manager.get_all_requests()
        report_path = report_gen.generate_history_report(history)
        
        return jsonify({
            'report_url': url_for('static', 
                                filename=f'results/{os.path.basename(report_path)}'),
            'filename': os.path.basename(report_path)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/statistics', methods=['GET'])
def get_statistics():
    """Получение статистики"""
    try:
        # Общая статистика
        history = db_manager.get_all_requests()
        
        total_requests = len(history)
        total_fruits = sum(req['total_fruits'] for req in history)
        
        # Статистика по фруктам
        fruit_stats = {}
        for req in history:
            for fruit, count in req['fruit_counts'].items():
                fruit_stats[fruit] = fruit_stats.get(fruit, 0) + count
        
        # Самый популярный фрукт
        most_common = max(fruit_stats.items(), key=lambda x: x[1]) if fruit_stats else ('Нет данных', 0)
        
        return jsonify({
            'total_requests': total_requests,
            'total_fruits': total_fruits,
            'fruit_statistics': fruit_stats,
            'most_common_fruit': {
                'name': most_common[0],
                'count': most_common[1]
            },
            'average_fruits_per_request': round(total_fruits / total_requests, 2) if total_requests > 0 else 0
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Запуск приложения для подсчета фруктов...")
    print("Модель YOLOv8 загружается... Это может занять некоторое время при первом запуске.")
    print("После запуска откройте: http://localhost:5000")
    
    # Запуск Flask приложения
    app.run(debug=True, host='0.0.0.0', port=5000)
