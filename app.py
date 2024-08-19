from flask import Flask, request, jsonify
from nudenet import NudeDetector
import os
import requests
import logging
from io import BytesIO
import cv2  # OpenCV for video processing

# Initialize the Flask app
app = Flask(__name__)

# Initialize the detector
detector = NudeDetector()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_frames(video_path, frame_rate=1):
    frames = []
    video_capture = cv2.VideoCapture(video_path)
    frame_count = 0
    while True:
        ret, frame = video_capture.read()
        if not ret:
            break
        if frame_count % frame_rate == 0:
            frame_path = os.path.join(os.getcwd(), f'frame_{frame_count}.jpg')
            cv2.imwrite(frame_path, frame)
            frames.append(frame_path)
        frame_count += 1
    video_capture.release()
    return frames

@app.route('/check_media_safety', methods=['POST'])
def check_media_safety():
    media_path = None
    try:
        if 'media' in request.files:
            media = request.files['media']
            media_path = os.path.join(os.getcwd(), media.filename)
            media.save(media_path)
            logger.info(f"Media file saved: {media_path}")
        elif 'media_url' in request.form:
            media_url = request.form['media_url']
            response = requests.get(media_url)
            if response.status_code == 200:
                media_path = os.path.join(os.getcwd(), media_url.split('/')[-1])
                with open(media_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"Media downloaded from URL and saved: {media_path}")
            else:
                logger.error(f"Content is not accessible via provided link: {media_url}, status code: {response.status_code}")
                return jsonify({'error': 'Content is not accessible via provided link'}), 400
        else:
            logger.error('No media provided')
            return jsonify({'error': 'No media provided'}), 400

        if media_path.endswith(('.jpg', '.jpeg', '.png', '.bmp')):
            # Detect nudity in the image
            result = detector.detect(media_path)
            logger.info(f"Detection result for image: {result}")
            if isinstance(result, list) and all('class' in r for r in result):
                nudity_detected = any(r['class'] in ['EXPOSED_ANUS', 'EXPOSED_BUTTOCKS', 'EXPOSED_BREAST_F', 'EXPOSED_GENITALIA_F', 'EXPOSED_GENITALIA_M', 'EXPOSED_BREAST_M'] for r in result)
                if nudity_detected:
                    violations = [{'type': r['class'], 'confidence': r['score']} for r in result if r['class'] in ['EXPOSED_ANUS', 'EXPOSED_BUTTOCKS', 'EXPOSED_BREAST_F', 'EXPOSED_GENITALIA_F', 'EXPOSED_GENITALIA_M', 'EXPOSED_BREAST_M']]
                    logger.info(f"Nudity detected in image with violations: {violations}")
                    return jsonify({'status': 'not safe', 'violations': violations})
                else:
                    logger.info('No nudity detected in image')
                    return jsonify({'status': 'safe'})
            else:
                logger.error('Unexpected result format from detector for image')
                return jsonify({'error': 'Unexpected result format from detector'}), 500

        elif media_path.endswith(('.mp4', '.avi', '.mov', '.mkv')):
            # Extract frames from the video
            frames = extract_frames(media_path, frame_rate=10)  # Adjust frame_rate as needed
            logger.info(f"Extracted {len(frames)} frames from video")
            nudity_detected = False
            violations = []
            for frame in frames:
                result = detector.detect(frame)
                logger.info(f"Detection result for frame {frame}: {result}")
                if isinstance(result, list) and all('class' in r for r in result):
                    for r in result:
                        if r['class'] in ['EXPOSED_ANUS', 'EXPOSED_BUTTOCKS', 'EXPOSED_BREAST_F', 'EXPOSED_GENITALIA_F', 'EXPOSED_GENITALIA_M', 'EXPOSED_BREAST_M']:
                            nudity_detected = True
                            violations.append({'type': r['class'], 'confidence': r['score']})
                else:
                    logger.error('Unexpected result format from detector for frame')
                    return jsonify({'error': 'Unexpected result format from detector'}), 500
                os.remove(frame)  # Clean up frame after processing
            if nudity_detected:
                logger.info(f"Nudity detected in video with violations: {violations}")
                return jsonify({'status': 'not safe', 'violations': violations})
            else:
                logger.info('No nudity detected in video')
                return jsonify({'status': 'safe'})
        else:
            logger.error('Unsupported media format')
            return jsonify({'error': 'Unsupported media format'}), 400

    except Exception as e:
        logger.error('An error occurred while processing media', exc_info=True)
        return jsonify({'error': 'An internal error occurred'}), 500

    finally:
        if media_path and os.path.exists(media_path):
            os.remove(media_path)
            logger.info(f"Temporary media file removed: {media_path}")

if __name__ == '__main__':
    app.run(debug=True)
