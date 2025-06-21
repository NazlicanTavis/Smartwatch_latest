from flask import Flask, request, jsonify
import json
import os
import joblib
import numpy as np
import librosa
from datetime import datetime
import requests

ageFilterMappingDict = {"twenties":0,"thirties":0,"fourties":0,"fifties":0,"sixties":0,"seventies":0, "eighties":0}

age_key_map = {
    "20s": "twenties",
    "30s": "thirties",
    "40s": "fourties",
    "50s": "fifties",
    "60s": "sixties",
    "70s": "seventies",
    "80s": "eighties"
}

# Load the trained model for emotion detection
with open('emotion_model.joblib', 'rb') as file:
    emotion_model = joblib.load(file)
# Load the trained age model for age detection
with open('age_model.joblib', 'rb') as file:
    age_model = joblib.load(file)
with open('gender_model.joblib', 'rb') as file:
    gender_model = joblib.load(file)

app = Flask(__name__)
UPLOAD_FOLDER = "./"

@app.route('/api/data', methods=['POST'])
def receive_data():
    data = request.get_json()
    print("Received:", data)
    print(f"Received Data type: ", type(data))

    # Extract phone numbers
    primary_phone = data.get('primaryPhone', '')
    secondary_phone = data.get('secondaryPhone', '')

    # Extract filters
    filters = data.get('filters', {})

    # Gender extraction
    gender = [g for g in ['Male', 'Female'] if filters.get(g) == 1]

    # Age groups extraction
    age_groups = [age for age in ['20s', '30s', '40s', '50s', '60s', '70s', '80s'] if filters.get(age) == 1]

    for age in age_key_map:
        if filters.get(age) == 1:
            ageFilterMappingDict[age_key_map[age]] = 1

    # Emotions extraction
    emotions_list = ['Angry', 'Sad', 'Neutral', 'Calm', 'Happy', 'Fear', 'Disgust', 'Surprised']
    emotions = [emotion for emotion in emotions_list if filters.get(emotion) == 1]

    # Display result
    print("Primary Phone:", primary_phone)
    print("Secondary Phone:", secondary_phone)
    print("Gender:", gender)
    print("Age Groups:", age_groups)
    print("Emotions:", emotions)
    
    
    with open("settings.txt","w") as file:
        json.dump(data, file)
        print("New settings saved successfully")
    return jsonify({"status": "success", "message": "Data received and saved."})

@app.route('/upload', methods=['POST'])
def upload_file():
    print("Received upload request")
    if 'file' not in request.files:
         return 'No file part', 400
    
    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400
    else:
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        print('File saved, starting prediction')
        return startPrediction(filepath)

def startPrediction(file_path):
    print(f"Starting prediction for: {file_path}")  # Add this
    feature = extract_feature(file_path, mfcc=True)

    if feature is not None:
        feature_2d = np.array([feature])  # Convert to 2D array
        emotion_prediction = emotion_model.predict(feature_2d)[0]
        age_prediction = age_model.predict(feature_2d)[0]
        gender_prediction = gender_model.predict(feature_2d)[0]
        current_time = datetime.now().strftime("%H:%M")
        result = check_anomaly(age_prediction, gender_prediction, emotion_prediction)

        # Send to your ASP.NET Core API
        send_to_csharp_api(
            timestamp=current_time,
            age=age_prediction,
            gender=gender_prediction,
            emotion=emotion_prediction,
            result=result,
            file_path=file_path
        )

        with open("results.txt", "a") as f:
            f.write(f"{current_time},{age_prediction},{gender_prediction},{emotion_prediction},{result}\n")

        print(f"Emotion Prediction: {emotion_prediction}, Gender Prediction: {gender_prediction}, Age Prediction: {age_prediction}, Timestamp: {current_time}")  # Debug print

        return jsonify({
            "emotion_prediction": emotion_prediction,
            "gender_prediction": gender_prediction,
            "age_prediction": age_prediction,
            "timestamp": current_time,
            "result": result
        })
    else:
        return jsonify({"error": "Feature extraction failed"}), 400

def extract_feature(file_name, mfcc=True):
    try:
        print(f"Entering extract_feature with file: {file_name}")  # Debug print so we can see if correct file was send
        X, sample_rate = librosa.load(file_name, res_type='kaiser_fast')
        print(f"Loaded file {file_name} with sample rate {sample_rate}")  # Debug print

        result = np.array([])

        if mfcc:
            print("Extracting MFCC features...")  # Debug print
            mfccs = np.mean(librosa.feature.mfcc(y=X, sr=sample_rate, n_mfcc=40).T, axis=0)
            print(f"MFCC features extracted: {mfccs}")  # Debug print
            result = np.hstack((result, mfccs)) if result.size else mfccs

        return result
    except Exception as e:
        print(f"Error processing file {file_name}: {e}")  # Debug print
        return None

def send_to_csharp_api(timestamp, age, gender, emotion, result, file_path):
    url = "https://smartwatchforchildsafety-bffrfaahgtahb9bg.italynorth-01.azurewebsites.net/api/smartwatch/data"

    # Format for ASP.NET Core Swagger-style form field names
    form_data = {
        "MetadataJson.timestamp": timestamp,
        "MetadataJson.age_prediction": age,
        "MetadataJson.gender_prediction": gender,
        "MetadataJson.emotion_prediction": emotion,
        "MetadataJson.result": result
    }

    files = {
        "WavFile": ("audio.wav", open(file_path, "rb"), "audio/wav")
    }

    try:
        response = requests.post(url, data=form_data, files=files)
        print("C# API response:", response.status_code, response.text)
    except Exception as e:
        print("Failed to send data to C# API:", e)

def check_anomaly(age_result:str, gender_result:str, emotion_result:str):
    with open("settings.txt","r") as file:
        content:dict = json.load(file)
        filters:dict = dict(content["filters"])
    if(filters[gender_result[0].capitalize()] == 1 or filters[emotion_result[0].capitalize()] == 1 or ageFilterMappingDict[age_result[0]] == 1):
        print("Anomaly detected. Informing parents.")
        return "ANOMALI"
    else:
        return "NORMAL"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=12000)