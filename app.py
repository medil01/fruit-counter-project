import os
import time
from datetime import datetime

from flask import Flask, jsonify, render_template, request, url_for
from flask_cors import CORS

from database import DatabaseManager
from fruit_detector import FruitDetector
from report_generator import ReportGenerator
from utils import cleanup_old_files, format_statistics, save_uploaded_file

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

UPLOAD_FOLDER = 'static/uploads'
RESULT_FOLDER = 'static/results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

detector = FruitDetector()
db_manager = DatabaseManager()
report_gen = ReportGenerator(RESULT_FOLDER)


@app.route('/')
def index():
    """Главная страница приложения."""
    history = db_manager.get_all_requests()[:10]
    daily_stats = db_manager.get_daily_statistics()
    return render_template('index.html', history=history, daily_stats=daily_stats)


@app.route('/upload', methods=['POST'])
def upload_file():
    """Обработка загрузки изображения и запуск детекции."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        filepath = save_uploaded_file(file, UPLOAD_FOLDER)
        if not filepath:
            return jsonify({'error': 'Invalid file type'}), 400

        start_time = time.time()
        statistics = detector.detect_fruits(filepath)

        if not statistics:
            return jsonify({'error': 'Failed to process image'}), 500

        processing_time = time.time() - start_time

        db_manager.save_request(
            filename=os.path.basename(filepath),
            statistics=statistics,
            processing_time=processing_time
        )

        result = format_statistics(statistics)
        result['processing_time'] = round(processing_time, 2)
        result['result_url'] = url_for(
            'static',
            filename=f'results/{os.path.basename(statistics["result_image"])}'
        )

        cleanup_old_files(UPLOAD_FOLDER)
        cleanup_old_files(RESULT_FOLDER)

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/history', methods=['GET'])
def get_history():
    """Получение полной истории запросов."""
    try:
        history = db_manager.get_all_requests()
        return jsonify(history)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/generate_report', methods=['POST'])
def generate_report():
    """Генерация отчета (PDF/Excel) для последнего запроса."""
    try:
        data = request.json
        report_type = data.get('type', 'pdf')

        history = db_manager.get_all_requests()
        if not history:
            return jsonify({'error': 'No data available for report'}), 400

        latest_request = history[0]
        stats_data = {
            'total_fruits': latest_request['total_fruits'],
            'fruit_counts': latest_request['fruit_counts']
        }

        if report_type == 'pdf':
            report_path = report_gen.generate_pdf_report(
                statistics=stats_data,
                request_data=latest_request
            )
        elif report_type == 'excel':
            report_path = report_gen.generate_excel_report(
                statistics=stats_data,
                request_data=latest_request
            )
        else:
            return jsonify({'error': 'Invalid report type'}), 400

        return jsonify({
            'report_url': url_for(
                'static',
                filename=f'results/{os.path.basename(report_path)}'
            ),
            'filename': os.path.basename(report_path)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/generate_history_report', methods=['GET'])
def generate_history_report():
    """Генерация сводного отчета по всей истории."""
    try:
        history = db_manager.get_all_requests()
        report_path = report_gen.generate_history_report(history)

        return jsonify({
            'report_url': url_for(
                'static',
                filename=f'results/{os.path.basename(report_path)}'
            ),
            'filename': os.path.basename(report_path)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/statistics', methods=['GET'])
def get_statistics():
    """Агрегация общей статистики."""
    try:
        history = db_manager.get_all_requests()

        total_requests = len(history)
        total_fruits = sum(req['total_fruits'] for req in history)

        fruit_stats = {}
        for req in history:
            for fruit, count in req['fruit_counts'].items():
                fruit_stats[fruit] = fruit_stats.get(fruit, 0) + count

        most_common = ('Нет данных', 0)
        if fruit_stats:
            most_common = max(fruit_stats.items(), key=lambda x: x[1])

        avg_fruits = round(total_fruits / total_requests, 2) if total_requests > 0 else 0

        return jsonify({
            'total_requests': total_requests,
            'total_fruits': total_fruits,
            'fruit_statistics': fruit_stats,
            'most_common_fruit': {
                'name': most_common[0],
                'count': most_common[1]
            },
            'average_fruits_per_request': avg_fruits
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
