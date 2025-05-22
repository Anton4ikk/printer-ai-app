### **Project Description**

1. This project provides demonstration of handless printer interface.
2. Instead of manual interact with printer app interface you could use voice commands.
3. To perform voice input you should click Rec button and say desirable action. Than click Stop button.
4. Available voice commands:
   * `Print {file_name}` (for example: `Print contract`)
   * `Scan`
   * `Copy`
   * `Publish {file_name}` (for example: `Publish photo one`)

### **How it works**

**1. Instructions**:

![](/media/pic.png)

**2. Example**:

![](/media/video.gif)

### **Setup Instructions**
**1. Install Packages**:
```bash
# Linux
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```
**2. Install Dependencies**:
```bash
pip install -r requirements.txt
```
**3. Run the App**:
```bash
python app.py
```
Application will be available at http://localhost:7777
