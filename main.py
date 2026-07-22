import os
from flask import Flask, jsonify

app = Flask(__name__)

# หน้าแรกสำหรับเช็กสถานะการทำงาน (Health Check)
@app.route('/')
def home():
    return jsonify({
        "status": "success",
        "message": "App is running smoothly on Render!",
        "port": os.environ.get("PORT", "5000")
    })

if __name__ == '__main__':
    # ดึงค่า PORT ที่ Render กำหนดมาให้โดยอัตโนมัติ
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
