import cv2
import time
import requests
import threading
import queue
from ultralytics import YOLO
import torch

from config import (
    RTSP_URL,
    TARGET_FPS,
    CONFIDENCE_THRESHOLD,
    COOLDOWN_SECONDS,
    MODEL_PATH,
    IMAGE_SIZE,
    DISPLAY_WIDTH,
    DISPLAY_HEIGHT
)

# ========== КЛАСС ДЛЯ РАБОТЫ С API ДОМОФОНА ==========
class DomofonAPI:
    def __init__(self):


    def open_door(self):  # Открытие домофона
        """
        Реализация намеренно удалена из публичной версии проекта.
        """
    return False

# ========== ОСНОВНАЯ ФУНКЦИЯ ==========
def main():
    print("=" * 60)
    print("Gesture Domofon — открытие домофона по жестам")
    print("=" * 60)
    print()

    # Инициализация API
    api = DomofonAPI()

    # Проверка CUDA
    cuda_available = torch.cuda.is_available()
    if cuda_available:
        print(f"CUDA доступна! GPU: {torch.cuda.get_device_name(0)}")
        device = "cuda"
    else:
        print("CUDA не найдена, работаем на CPU ")
        device = "cpu"

    # Загрузка модели YOLO
    print("\n📦 Загрузка модели YOLO...")
    try:
        model = YOLO(MODEL_PATH)
        if cuda_available:
            model.to(device)
        print(f"Модель загружена на {device.upper()}")
    except Exception as e:
        print(f"Файл {MODEL_PATH} не найден! {e}")
        return

    # Подключение к RTSP
    print(f"\nПодключение к камере...")
    print(f"{RTSP_URL[:80]}...")

    cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)

    if not cap.isOpened():
        print("❌ Не удалось подключиться к камере")
        return

    print("✅ Поток открыт!")

    FRAME_INTERVAL = 1.0 / TARGET_FPS

    last_open_time = 0
    last_detection_time = 0

    # Переменные для отображения
    last_result = {"has_thumbs_up": False, "has_ok": False}

    # Очередь для кадров
    frame_queue = queue.Queue(maxsize=1)
    
    # Поток захвата видео
    def capture_thread():
        local_cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
        while True:
            ret, frame = local_cap.read()
            if ret:
                try:
                    if frame_queue.full():
                        frame_queue.get_nowait()
                    frame_queue.put(frame)
                except queue.Full:
                    pass
            else:
                time.sleep(0.01)
    
    
    # Поток распознавания жестов
    def detection_thread():
        nonlocal last_result, last_detection_time
        while True:
            current_time = time.time()

            if current_time - last_detection_time >= FRAME_INTERVAL:
                try:
                    frame = frame_queue.get(timeout=1.0)
                    small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)

                    results = model(small_frame, verbose=False, imgsz=IMAGE_SIZE, device=device)

                    detected_classes = []
                    for r in results:
                        boxes = r.boxes
                        if boxes is not None:
                            for box in boxes:
                                cls_id = int(box.cls[0])
                                class_name = model.names[cls_id]
                                confidence = float(box.conf[0])
                                if confidence > CONFIDENCE_THRESHOLD and class_name in ["thumbs_up", "ok"]:
                                    detected_classes.append(class_name)

                    last_result = {
                        "has_thumbs_up": "thumbs_up" in detected_classes,
                        "has_ok": "ok" in detected_classes
                    }
                    last_detection_time = current_time

                except queue.Empty:
                    pass
                except Exception as e:
                    pass

            time.sleep(0.01)

    # threading
    t_capture = threading.Thread(target=capture_thread, daemon=True)
    t_detection = threading.Thread(target=detection_thread, daemon=True)
    t_capture.start()
    t_detection.start()

    print("WORKING! Нажмите 'q' для выхода\n")


    # Главный цикл – отображение
    while True:
        current_time = time.time()

        try:
            display_frame = frame_queue.get(timeout=0.1)
        except:
            continue

        has_thumbs_up = last_result["has_thumbs_up"]
        has_ok = last_result["has_ok"]

        if has_thumbs_up and has_ok:
            cv2.putText(display_frame, "BOTH GESTURES DETECTED!", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            if current_time - last_open_time > COOLDOWN_SECONDS:
                print(f"🟢 Обнаружены оба жеста! Открываю дверь...")
                cv2.putText(display_frame, "OPENING DOOR...", (50, 100),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

                if api.open_door():
                    print("✅ ДВЕРЬ ОТКРЫТА!")
                    last_open_time = current_time
                else:
                    print("❌ Ошибка открытия двери")
            else:
                wait_time = COOLDOWN_SECONDS - int(current_time - last_open_time)
                cv2.putText(display_frame, f"WAIT {wait_time}s", (50, 100),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 100, 255), 2)
        elif has_thumbs_up:
            cv2.putText(display_frame, "THUMBS UP detected - need OK", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 100, 255), 2)
        elif has_ok:
            cv2.putText(display_frame, "OK detected - need THUMBS UP", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 100, 255), 2)
        else:
            cv2.putText(display_frame, "Waiting for gestures...", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 2)

        status = "READY" if (has_thumbs_up and has_ok) else "DETECTING"
        color = (0, 255, 0) if (has_thumbs_up and has_ok) else (0, 100, 255)
        cv2.putText(display_frame, f"STATUS: {status}", (10, display_frame.shape[0] - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        cv2.putText(display_frame, f"GPU: {cuda_available}", (10, display_frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        cv2.imshow("Gesture Control", display_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("BYE BYE!")
            time.sleep(2)
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()