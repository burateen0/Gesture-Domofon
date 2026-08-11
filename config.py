# ===== RTSP-поток =====
RTSP_URL = "rtsp://"

# ===== Данные для API домофона =====

# ===== Настройки обработки =====
TARGET_FPS = 4                    # Частота анализа кадров
CONFIDENCE_THRESHOLD = 0.4        # Порог уверенности для детекции
COOLDOWN_SECONDS = 5              # Пауза между открытиями двери (сек)
MODEL_PATH = "best.pt"            # Путь к обученной модели
IMAGE_SIZE = 640                  # Размер для инференса (YOLO imgsz)

DISPLAY_WIDTH = 1280
DISPLAY_HEIGHT = 720