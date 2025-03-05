import os
import sqlite3
import uuid
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

UPLOAD_FOLDER = os.path.join('data', 'image')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
DATABASE = 'answers.db'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            description TEXT,
            action TEXT,
            participant TEXT,
            area TEXT,
            category TEXT,
            state TEXT,
            shift TEXT,
            image TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory('data', filename)

@app.route('/')
def index():
    filters = {}
    query = "SELECT * FROM posts WHERE 1=1"
    params = []
    if request.args.get('participant'):
        query += " AND participant = ?"
        params.append(request.args.get('participant'))
        filters['participant'] = request.args.get('participant')
    if request.args.get('area'):
        query += " AND area = ?"
        params.append(request.args.get('area'))
        filters['area'] = request.args.get('area')
    if request.args.get('category'):
        query += " AND category = ?"
        params.append(request.args.get('category'))
        filters['category'] = request.args.get('category')
    if request.args.get('state'):
        query += " AND state = ?"
        params.append(request.args.get('state'))
        filters['state'] = request.args.get('state')
    if request.args.get('shift'):
        query += " AND shift = ?"
        params.append(request.args.get('shift'))
        filters['shift'] = request.args.get('shift')
    query += " ORDER BY timestamp DESC"
    conn = get_db_connection()
    posts = conn.execute(query, params).fetchall()
    conn.close()
    return render_template('index.html', posts=posts, filters=filters)

@app.route('/post/<int:post_id>')
def view_post(post_id):
    conn = get_db_connection()
    post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    conn.close()
    if post is None:
        return "Пост не найден", 404
    return render_template('view_post.html', post=post)

@app.route('/create', methods=['GET', 'POST'])
def create_post():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        action = request.form.get('action')
        participant = request.form.get('participant')
        area = request.form.get('area')
        category = request.form.get('category')
        state_val = request.form.get('state')
        shift = request.form.get('shift')
        user_id = 0  # Замените, если нужна аутентификация
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = str(uuid.uuid4()) + "_" + filename
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(save_path)
                image_path = save_path
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO posts (user_id, title, description, action, participant, area, category, state, shift, image)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, title, description, action, participant, area, category, state_val, shift, image_path))
        conn.commit()
        conn.close()
        flash('Пост успешно создан!', 'success')
        return redirect(url_for('index'))
    return render_template('create.html')

if __name__ == '__main__':
    app.run(debug=True)
