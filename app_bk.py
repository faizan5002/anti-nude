from flask import Flask, request, jsonify
from nudenet import NudeDetector
import os
import requests
from io import BytesIO
from PIL import Image, UnidentifiedImageError

# Initialize the Flask app
app = Flask(__name__)

# Initialize the detector
detector = NudeDetector()

@app.route('/check_image_safety', methods=['POST'])
def check_image_safety():
    image_path = None
    
    try:
        # Check if an image file was uploaded
        if 'image' in request.files:
            image = request.files['image']
            image_path = os.path.join(os.getcwd(), image.filename)
            image.save(image_path)
        elif 'image_url' in request.form:
            image_url = request.form['image_url']
            response = requests.get(image_url)
            if response.status_code == 200:
                try:
                    image = Image.open(BytesIO(response.content))
                    image_path = os.path.join(os.getcwd(), 'temp_image.jpg')
                    image.save(image_path)
                except UnidentifiedImageError:
                    return jsonify({'error': 'The URL does not point to a valid image file'}), 400
            else:
                return jsonify({'error': 'Unable to download image from URL'}), 400
        else:
            return jsonify({'error': 'No image provided'}), 400

        # Detect nudity in the image
        result = detector.detect(image_path)

        # If the result list is empty, the content is likely safe
        if not result:
            return jsonify({'status': 'safe'})
        else:
            violations = []
            for r in result:
                violation_type = r.get('label', 'unknown violation')
                confidence = r.get('score', 0)
                violations.append({'type': violation_type, 'confidence': confidence})
            
            return jsonify({'status': 'not safe', 'violations': violations})

    finally:
        # Clean up: Remove the temporary image file if it was created
        if image_path and os.path.exists(image_path):
            os.remove(image_path)

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
