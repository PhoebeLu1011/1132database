from flask import Flask, render_template, request, send_file
import os
from ai_module import agent_analyze_and_suggest, generate_pdf, open_keep_and_fill
from werkzeug.utils import secure_filename
import pandas as pd
from flask_socketio import SocketIO
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
from threading import Thread
import matplotlib.dates as mdates

matplotlib.use('Agg')
matplotlib.rc('font', family='Microsoft JhengHei')

app = Flask(__name__)
socketio = SocketIO(app)


app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
STATIC_FOLDER = "static"
MOODTREND_FOLDER = os.path.join(STATIC_FOLDER, "moodtrend")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)
os.makedirs(MOODTREND_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def generate_exercise_mood_plot(user_entries, df): 

    try:
        x_labels = df["日期"].astype(str).tolist()

            
# 畫圖
        fig, ax1 = plt.subplots(figsize=(12, 6))
        ax2 = ax1.twinx()

        ax1.plot(x_labels, df["心情(1-10)"], 'bo-', label="心情(1-10)")
        ax2.plot(x_labels, df["運動時間(分鐘)"], 'go-', label="運動時間(分鐘)")

        ax1.set_ylabel("心情 (1-10)", color="blue")
        ax2.set_ylabel("運動時間 (分鐘)", color="green")

        ax1.tick_params(axis='y', labelcolor='blue')
        ax2.tick_params(axis='y', labelcolor='green')

        avg_mood = df["心情(1-10)"].mean()
        avg_exer = df["運動時間(分鐘)"].mean()

        ax1.axhline(y=avg_mood, color='blue', linestyle='--', label=f"心情平均 ({avg_mood:.2f})")
        ax2.axhline(y=avg_exer , color='green', linestyle='--', label=f"運動時間平均 ({avg_exer :.2f})")

        plt.xticks(rotation=45)  # ✅ 轉斜讓文字不擠
        plt.title("本週心情與運動趨勢圖")
        fig.tight_layout()


        output_path = os.path.join("static", "moodtrend", "exercise_mood_.png")
        plt.savefig(output_path)
        plt.close()
        return output_path

    except Exception as e:
        print(" 畫圖錯誤：", e)
        return None

        
@app.route("/", methods=["GET", "POST"])
def index():
    ai_output = ""
    pdf_path = ""
    stats = {}
    chart_path = None

    if request.method == "POST":
        file = request.files.get("csv_file")
        user_prompt = request.form.get("user_prompt", "")

        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)


            ai_output = agent_analyze_and_suggest(filepath, user_prompt)
            pdf_path = generate_pdf(ai_output)

            try:
                df = pd.read_csv(filepath)
                if '心情(1-10)' in df.columns and '運動時間(分鐘)' in df.columns:
                    chart_path = generate_exercise_mood_plot(user_id="user1", df=df)
                if '心情(1-10)' in df.columns and '主觀疲勞感(1-10)' in df.columns and '運動時間' in df.columns:
                    stats = {
                        "平均心情": round(df['心情(1-10)'].mean(), 2),
                        "平均疲勞感": round(df['主觀疲勞感(1-10)'].mean(), 2),
                        "總運動時間": df['運動時間(分鐘)'].sum()
                    }
            except Exception as e:
                print("資料處理錯誤：", e)
            
            Thread(target=background_task, args=(filepath,)).start()

            return render_template("hw5_1.html", ai_output=ai_output, pdf_path=pdf_path, stats=stats, filepath=filepath)
        else:
            ai_output = agent_analyze_and_suggest(None, user_prompt)
            pdf_path = generate_pdf(ai_output)
            return render_template("hw5_1.html", ai_output=ai_output, pdf_path=pdf_path, stats=stats, filepath=filepath)

    return render_template("hw5_1.html", ai_output=None, stats=None, filepath=None)

def background_task(file_path):
    try:
        df = pd.read_csv(file_path)
        user_id = os.path.splitext(os.path.basename(file_path))[0]

        print("✅ 即將產生圖表...")
        plot_path = generate_exercise_mood_plot(user_id, df)
        print("✅ 圖表產生完成，路徑：", plot_path)

        if plot_path:
            socketio.emit('plot_generated', {'plot_url': '/' + plot_path})
        else:
            socketio.emit('update', {'message': '❌ 圖表產生失敗！'})

    except Exception as e:
        socketio.emit('update', {'message': f"❌ 錯誤：{str(e)}"})


@app.route("/download")
def download_pdf():
    path = request.args.get("path")
    return send_file(path, as_attachment=True)

@app.route("/keep", methods=["POST"])
def send_to_keep():
    note_text = request.form.get("keep_text", "")
    open_keep_and_fill(note_text)
    return "已關閉 Google Keep"

@socketio.on('generate_plot')
def handle_generate_plot(data):
    file_path = data.get('filepath')
    if not file_path:
        socketio.emit('update', {'message': '❌ 未提供檔案路徑'})
        return

    try:
        df = pd.read_csv(file_path)
        user_id = os.path.splitext(os.path.basename(file_path))[0]
        plot_path = generate_exercise_mood_plot(user_id, df)
        if plot_path:
            socketio.emit('plot_generated', {'plot_url': '/' + plot_path})
        else:
            socketio.emit('update', {'message': '❌ 圖表產生失敗'})
    except Exception as e:
        socketio.emit('update', {'message': f"❌ 錯誤：{str(e)}"})


if __name__ == "__main__":
    app.run(debug=True)
