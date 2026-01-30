import torch
import cv2
import numpy as np
from PIL import Image
from ultralytics import YOLO
import os

class FruitDetector:
    def __init__(self, model_path='yolov8n.pt'):
        """
        Инициализация детектора фруктов с предобученной моделью YOLOv8
        """
        # Используем YOLOv8 - современную и быструю модель для детекции объектов
        # Модель автоматически скачается при первом запуске
        self.model = YOLO(model_path)
        
        # Классы фруктов в COCO dataset (базовая модель знает основные фрукты)
        self.fruit_classes = {
            47: 'apple',
            48: 'orange',
            49: 'banana',
            50: 'broccoli',
            51: 'carrot',
            52: 'hot dog',  # не фрукт, но может быть в списке
            53: 'pizza',
            54: 'donut',
            55: 'cake'
        }
        
        # Настройки детекции
        self.confidence_threshold = 0.25
        self.iou_threshold = 0.45
        
    def detect_fruits(self, image_path):
        """
        Обнаружение фруктов на изображении
        """
        try:
            # Загрузка изображения
            image = Image.open(image_path)
            img_array = np.array(image)
            
            # Детекция объектов с помощью YOLOv8
            results = self.model(
                source=img_array,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                classes=list(self.fruit_classes.keys())  # Только фрукты
            )
            
            # Обработка результатов
            detections = []
            total_fruits = 0
            fruit_counts = {}
            
            # Создаем копию изображения для аннотаций
            annotated_img = img_array.copy()
            
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        # Координаты ограничивающего прямоугольника
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = box.conf[0].cpu().numpy()
                        class_id = int(box.cls[0].cpu().numpy())
                        
                        # Проверяем, что это фрукт из нашего списка
                        if class_id in self.fruit_classes:
                            fruit_name = self.fruit_classes[class_id]
                            
                            # Добавляем детекцию в список
                            detection = {
                                'fruit': fruit_name,
                                'confidence': float(confidence),
                                'bbox': [float(x1), float(y1), float(x2), float(y2)],
                                'area': float((x2 - x1) * (y2 - y1))
                            }
                            detections.append(detection)
                            
                            # Обновляем счетчики
                            total_fruits += 1
                            fruit_counts[fruit_name] = fruit_counts.get(fruit_name, 0) + 1
                            
                            # Рисуем bounding box на изображении
                            cv2.rectangle(annotated_img, 
                                        (int(x1), int(y1)), 
                                        (int(x2), int(y2)), 
                                        (0, 255, 0), 2)
                            
                            # Добавляем текст с названием фрукта и уверенностью
                            label = f"{fruit_name}: {confidence:.2f}"
                            cv2.putText(annotated_img, label, 
                                      (int(x1), int(y1) - 10),
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, 
                                      (0, 255, 0), 2)
            
            # Сохраняем аннотированное изображение
            result_path = os.path.join('static', 'results', 
                                     f'result_{os.path.basename(image_path)}')
            cv2.imwrite(result_path, cv2.cvtColor(annotated_img, cv2.COLOR_RGB2BGR))
            
            # Подготавливаем статистику
            statistics = {
                'total_fruits': total_fruits,
                'fruit_counts': fruit_counts,
                'detections': detections,
                'result_image': result_path,
                'original_image': image_path
            }
            
            return statistics
            
        except Exception as e:
            print(f"Ошибка при детекции: {str(e)}")
            return None
    
    def count_from_video(self, video_path, frame_interval=10):
        """
        Подсчет фруктов из видео (для конвейера)
        """
        cap = cv2.VideoCapture(video_path)
        frame_count = 0
        total_counts = {}
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            if frame_count % frame_interval == 0:
                # Конвертируем кадр для обработки
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Временное сохранение кадра
                temp_path = f'temp_frame_{frame_count}.jpg'
                cv2.imwrite(temp_path, frame)
                
                # Детекция на кадре
                stats = self.detect_fruits(temp_path)
                
                if stats:
                    for fruit, count in stats['fruit_counts'].items():
                        total_counts[fruit] = total_counts.get(fruit, 0) + count
                
                # Удаляем временный файл
                os.remove(temp_path)
            
            frame_count += 1
            
        cap.release()
        return total_counts
