from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from sentence_transformers import SentenceTransformer, util
from collections import defaultdict
import whisper
import tempfile
import subprocess
import os

app = Flask(__name__)
CORS(app)
model = whisper.load_model("base")

class ActionMatcher:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.actions = {
            "print": {
                "patterns": ["print", "generate hard copy"],
                "files": {
                    "Photo_1.png": ["photo one", "photo 1", "photo one picture", "first image", "initial picture"],
                    "Contract.pdf": ["contract", "contract pdf", "agreement document", "legal paper"],
                    "ID.pdf": ["id", "id pdf", "id document", "identification document", "identity card"],
                    "Demo.jpg": ["demo", "demo picture", "demo photo", "demonstration photo", "demonstration picture", "example image"],
                    "1234.pdf": ["one two three four", "1234", "1234 pdf", "1234 document", "document 1234", "four numbers"],
                    "Mountains.jpg": ["mountains", "mountain", "mountains picture", "mountains photo", "mountain view", "landscape photo"]
                },
                "template": "Print {file_name}"
            },
            "publish": {
                "patterns": ["publish to cloud", "upload"],
                "files": {
                    "Photo_1.png": ["photo one", "photo 1", "photo one picture", "first image", "initial picture"],
                    "Contract.pdf": ["contract", "contract pdf", "agreement document", "legal paper"],
                    "ID.pdf": ["id", "id pdf", "id document", "identification document", "identity card"],
                    "Demo.jpg": ["demo", "demo picture", "demo photo", "demonstration photo", "demonstration picture", "example image"],
                    "1234.pdf": ["one two three four", "1234", "1234 pdf", "1234 document", "document 1234", "four numbers"],
                    "Mountains.jpg": ["mountains", "mountains picture", "mountains photo", "mountain view", "landscape photo"]
                },
                "template": "Publish {file_name} to cloud"
            },
            "copy": {
                "patterns": ["copy", "copy document", "copy paper"],
                "template": "Copy"
            },
            "scan": {
                "patterns": ["scan", "scan document", "scan paper"],
                "template": "Scan"
            }
        }
        self.action_patterns = []
        self.action_map = []
        self.file_references = defaultdict(list)
        self.file_mappings = defaultdict(dict)
        self.file_embeddings = {}
        self._precompute_embeddings()

    def _precompute_embeddings(self):
        for action, config in self.actions.items():
            patterns = config["patterns"]
            if isinstance(patterns, str):
                patterns = [patterns]
            self.action_patterns.extend(patterns)
            self.action_map.extend([action] * len(patterns))

        if self.action_patterns:
            self.action_embeddings = self.model.encode(
                self.action_patterns, convert_to_tensor=True
            )

        for action, config in self.actions.items():
            files = config.get("files")
            if not isinstance(files, dict):
                continue

            phrases = []
            for filename, refs in files.items():
                if isinstance(refs, str):
                    refs = [refs]
                for ref in refs:
                    self.file_mappings[action][ref] = filename
                    self.file_references[action].append(ref)
                    phrases.append(ref)

            if phrases:
                self.file_embeddings[action] = self.model.encode(
                    phrases, convert_to_tensor=True
                )

    def _find_action(self, text, threshold=0.6):
        if not hasattr(self, 'action_embeddings') or self.action_embeddings.nelement() == 0:
            return None, 0.0

        text_embedding = self.model.encode(text, convert_to_tensor=True)
        cos_scores = util.cos_sim(text_embedding, self.action_embeddings)[0]
        best_score_idx = cos_scores.argmax().item()
        score = cos_scores[best_score_idx].item()  # Convert to Python float

        if score > threshold:
            return self.action_map[best_score_idx], score
        return None, 0.0

    def _match_reference(self, action, text, threshold=0.5):
        if action not in self.file_embeddings or self.file_embeddings[action].nelement() == 0:
            return "unknown_document", 0.0

        text_embedding = self.model.encode(text, convert_to_tensor=True)
        cos_scores = util.cos_sim(text_embedding, self.file_embeddings[action])[0]
        best_score_idx = cos_scores.argmax().item()
        score = cos_scores[best_score_idx].item()  # Convert to Python float

        if score > threshold:
            matched_phrase = self.file_references[action][best_score_idx]
            return self.file_mappings[action][matched_phrase], score

        return "unknown_document", 0.0

    def process(self, text, action_threshold=0.6, file_threshold=0.5):
        action, action_conf = self._find_action(text, action_threshold)
        if not action:
            return {"error": "No matching action found"}

        output = self.actions[action]["template"]
        if "files" in self.actions[action]:
            filename, file_conf = self._match_reference(action, text, file_threshold)
            try:
                if filename:
                    output = output.format(file_name=filename)
                else:
                    return {"error": "No file matched for action: {}".format(action)}
            except KeyError:
                return {"error": f"Template formatting error for {filename}"}

            return {
                "action": action,
                "output": output,
                "confidence": min(action_conf, file_conf)
            }

        return {
            "action": action,
            "output": output,
            "confidence": action_conf
        }

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file"}), 400

    try:
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as tmp_input:
            request.files['audio'].save(tmp_input.name)
            input_path = tmp_input.name

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_output:
            output_path = tmp_output.name

        cmd = ['ffmpeg',
            '-i', input_path,
            '-acodec', 'pcm_s16le',
            '-ac', '1',
            '-ar', '16000',
            '-y',
            output_path]
        subprocess.run(cmd, check=True, capture_output=True)
        transcription_result = model.transcribe(output_path)
        transcript_text = transcription_result.get('text', '').strip()

        if not transcript_text:
            return jsonify({
                "text": "",
                "rawText": "No speech detected",
            })

        matcher = ActionMatcher()
        result = matcher.process(transcription_result['text'])
        return jsonify({"text": result['output'], "rawText": transcription_result['text']})

    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Audio conversion failed: {e.stderr.decode()}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        for path in [input_path, output_path]:
            if path and os.path.exists(path):
                os.unlink(path)

if __name__ == '__main__':
    app.run(ssl_context=('certs/cert.pem', 'certs/key.pem'), host='0.0.0.0', port=7777)
    # app.run(host='0.0.0.0', port=7777)