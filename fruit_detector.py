import os

import cv2
from ultralytics import YOLO


class FruitDetector:
    """
    Класс для детекции и подсчета фруктов с использованием YOLOv8.
    Динамически определяет ID классов на основе загруженной модели.
    """

    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        target_fruits=None,
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.6,
    ):
        self.model = YOLO(model_path)

        if target_fruits is None:
            target_fruits = {"apple", "banana", "orange"}

        # Приведение model.names к единому формату dict
        names = self.model.names
        if isinstance(names, dict):
            id_to_name = {int(k): str(v) for k, v in names.items()}
        else:
            id_to_name = {i: str(n) for i, n in enumerate(names)}

        # Фильтрация ID целевых классов
        self.fruit_classes = {
            class_id: name for class_id, name in id_to_name.items() if name in target_fruits
        }
        self.fruit_class_ids = sorted(self.fruit_classes.keys())

        if not self.fruit_class_ids:
            raise ValueError(
                "Не найдены классы фруктов в модели. "
                "Проверьте веса (model_path) и target_fruits."
            )

        self.confidence_threshold = float(confidence_threshold)
        self.iou_threshold = float(iou_threshold)

    def detect_fruits(self, image_path: str):
        """Обнаружение и подсчет фруктов на изображении."""
        try:
            results = self.model.predict(
                source=image_path,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                classes=self.fruit_class_ids,
                verbose=False,
            )

            if not results:
                return None

            result = results[0]

            detections = []
            total_fruits = 0
            fruit_counts = {}

            annotated_img = result.plot()

            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    confidence = float(box.conf[0].item())
                    class_id = int(box.cls[0].item())

                    fruit_name = self.fruit_classes.get(class_id)
                    if fruit_name is None:
                        continue

                    detections.append(
                        {
                            "fruit": fruit_name,
                            "confidence": confidence,
                            "bbox": [float(x1), float(y1), float(x2), float(y2)],
                            "area": float((x2 - x1) * (y2 - y1)),
                        }
                    )

                    total_fruits += 1
                    fruit_counts[fruit_name] = fruit_counts.get(fruit_name, 0) + 1

            os.makedirs(os.path.join("static", "results"), exist_ok=True)
            result_path = os.path.join(
                "static",
                "results",
                f"result_{os.path.basename(image_path)}",
            )
            cv2.imwrite(result_path, annotated_img)

            return {
                "total_fruits": total_fruits,
                "fruit_counts": fruit_counts,
                "detections": detections,
                "result_image": result_path,
                "original_image": image_path,
            }

        except Exception as e:
            print(f"Ошибка при детекции: {str(e)}")
            return None

    def count_from_video(self, video_path: str, frame_interval: int = 10):
        """
        Покадровый подсчет фруктов из видео.
        Используется выборка кадров с заданным интервалом.
        """
        cap = cv2.VideoCapture(video_path)
        frame_count = 0
        total_counts = {}

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % frame_interval == 0:
                temp_path = f"temp_frame_{frame_count}.jpg"
                cv2.imwrite(temp_path, frame)

                stats = self.detect_fruits(temp_path)
                if stats:
                    for fruit, count in stats["fruit_counts"].items():
                        total_counts[fruit] = total_counts.get(fruit, 0) + count

                try:
                    os.remove(temp_path)
                except OSError:
                    pass

            frame_count += 1

        cap.release()
        return total_counts
