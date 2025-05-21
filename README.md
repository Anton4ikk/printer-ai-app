### **Setup Instructions**

**Install Dependencies**:
```bash
# Linux
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

```bash
pip install flask flask-cors openai-whisper ffmpeg-python sentence-transformers
```

**Run the Backend**:
```bash
python app.py
```

**Serve the Frontend**:
```bash
python -m http.server 8888
```