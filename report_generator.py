from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import pandas as pd
from datetime import datetime
import json
import os

class ReportGenerator:
    def __init__(self, output_dir='static/results'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_pdf_report(self, statistics, request_data):
        """Генерация PDF отчета"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"fruit_report_{timestamp}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        
        # Создаем PDF документ
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Заголовок
        title = Paragraph("Отчет по подсчету фруктов", styles['Title'])
        story.append(title)
        
        # Время создания
        date_str = Paragraph(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                           styles['Normal'])
        story.append(date_str)
        
        # Статистика
        stats_data = [
            ["Показатель", "Значение"],
            ["Всего фруктов", str(statistics['total_fruits'])],
            ["Изображение", os.path.basename(request_data['filename'])],
            ["Время обработки", f"{request_data['processing_time']:.2f} сек"]
        ]
        
        # Добавляем количество по каждому фрукту
        for fruit, count in statistics['fruit_counts'].items():
            stats_data.append([f"Количество {fruit}", str(count)])
        
        # Создаем таблицу
        stats_table = Table(stats_data)
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(stats_table)
        
        # Сохраняем PDF
        doc.build(story)
        return filepath
    
    def generate_excel_report(self, statistics, request_data):
        """Генерация Excel отчета"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"fruit_report_{timestamp}.xlsx"
        filepath = os.path.join(self.output_dir, filename)
        
        # Создаем DataFrame с основной статистикой
        data = {
            'Показатель': ['Всего фруктов', 'Изображение', 'Время обработки (сек)'],
            'Значение': [
                statistics['total_fruits'],
                os.path.basename(request_data['filename']),
                f"{request_data['processing_time']:.2f}"
            ]
        }
        
        df_main = pd.DataFrame(data)
        
        # DataFrame с детальной статистикой по фруктам
        fruit_data = []
        for fruit, count in statistics['fruit_counts'].items():
            fruit_data.append([fruit, count])
        
        df_fruits = pd.DataFrame(fruit_data, columns=['Фрукт', 'Количество'])
        
        # Создаем Excel writer
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df_main.to_excel(writer, sheet_name='Общая статистика', index=False)
            df_fruits.to_excel(writer, sheet_name='Статистика по фруктам', index=False)
            
            # Настраиваем ширину колонок
            worksheet = writer.sheets['Общая статистика']
            worksheet.column_dimensions['A'].width = 25
            worksheet.column_dimensions['B'].width = 20
            
            worksheet = writer.sheets['Статистика по фруктам']
            worksheet.column_dimensions['A'].width = 20
            worksheet.column_dimensions['B'].width = 15
        
        return filepath
    
    def generate_history_report(self, history_data):
        """Генерация отчета по истории запросов"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"history_report_{timestamp}.xlsx"
        filepath = os.path.join(self.output_dir, filename)
        
        # Конвертируем историю в DataFrame
        data = []
        for item in history_data:
            data.append({
                'Дата и время': item['timestamp'],
                'Файл': item['filename'],
                'Всего фруктов': item['total_fruits'],
                'Время обработки (сек)': item['processing_time']
            })
        
        df = pd.DataFrame(data)
        
        # Сохраняем в Excel
        df.to_excel(filepath, index=False)
        
        return filepath
