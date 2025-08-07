from flask import Flask, render_template, request, send_file, url_for
import os
import mysql.connector
import uuid
from PIL import Image
import numpy as np
from io import BytesIO
import base64

app = Flask(__name__)

# MySQL configuration
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="2903200S*",
    database="image_encryption"
)
cursor = db.cursor()

# In-memory storage for encrypted images
encrypted_images = {}

# Caesar Cipher Encrypt
def caesar_cipher_encrypt(text, shift=3):
    result = ""
    for char in text:
        if char.isalpha():
            base = ord('A') if char.isupper() else ord('a')
            result += chr((ord(char) - base + shift) % 26 + base)
        else:
            result += char
    return result

# Caesar Cipher Decrypt
def caesar_cipher_decrypt(text, shift=3):
    return caesar_cipher_encrypt(text, -shift)

# LSB Encryption
def encrypt_message(image_stream, message):
    try:
        if not message or len(message.strip()) == 0:
            return None, None, "Error: Message cannot be empty."

        cipher_text = caesar_cipher_encrypt(message)
        cipher_text += chr(0)  # Null terminator

        img = Image.open(image_stream).convert('RGB')
        data = np.array(img)
        flat_data = data.flatten()

        binary_message = ''.join([format(ord(char), '08b') for char in cipher_text])

        if len(binary_message) > len(flat_data):
            return None, None, "Error: Message too long for the image."

        for i in range(len(binary_message)):
            flat_data[i] = (flat_data[i] & 0b11111110) | int(binary_message[i])

        encrypted_data = flat_data.reshape(data.shape)
        encrypted_image = Image.fromarray(encrypted_data.astype('uint8'), 'RGB')

        img_io = BytesIO()
        encrypted_image.save(img_io, 'PNG')
        img_io.seek(0)

        base64_encoded_image = base64.b64encode(img_io.getvalue()).decode('utf-8')
        return img_io, base64_encoded_image, None

    except Exception as e:
        return None, None, f"Encryption Error: {str(e)}"

# LSB Decryption
def decrypt_message(image_bytes, entered_password, image_id):
    try:
        cursor.execute("SELECT password FROM image_data WHERE image_id = %s", (image_id,))
        result = cursor.fetchone()

        if not result:
            return "Error: Image ID not found."
        stored_password = result[0]
        if entered_password != stored_password:
            return "YOU ARE NOT AUTHORIZED!"

        image_stream = BytesIO(image_bytes)
        img = Image.open(image_stream).convert('RGB')
        data = np.array(img).flatten()

        bits = [str(pixel & 1) for pixel in data]
        chars = [chr(int(''.join(bits[i:i+8]), 2)) for i in range(0, len(bits), 8)]

        message = ''
        for c in chars:
            if c == chr(0):
                break
            message += c

        plain_text = caesar_cipher_decrypt(message)
        return plain_text
    except Exception as e:
        return f"Decryption Error: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/encrypt', methods=['GET', 'POST'])
def encrypt():
    if request.method == 'POST':
        image = request.files.get('image')
        message = request.form.get('message')
        password = request.form.get('password')

        if not image or not message or not password:
            return render_template('encrypt.html', error="All fields are required.")

        encrypted_io, base64_image, error = encrypt_message(image.stream, message)
        if error:
            return render_template('encrypt.html', error=error)

        try:
            image_id = str(uuid.uuid4())
            filename = image.filename

            encrypted_images[image_id] = {
                'filename': filename,
                'data': encrypted_io
            }

            cursor.execute(
                "INSERT INTO image_data (image_id, image_name, password) VALUES (%s, %s, %s)",
                (image_id, filename, password)
            )
            db.commit()

            download_url = url_for('download', image_id=image_id)

            return render_template(
                'encrypt.html',
                success=True,
                image_id=image_id,
                download_url=download_url,
                base64_image=base64_image
            )
        except Exception as e:
            return render_template('encrypt.html', error=f"MySQL Error: {str(e)}")

    return render_template('encrypt.html')

@app.route('/download/<image_id>')
def download(image_id):
    image_entry = encrypted_images.get(image_id)
    if not image_entry:
        return "Image not found or expired", 404

    image_io = image_entry['data']
    image_io.seek(0)
    filename = f"encrypted_{image_entry['filename']}"

    return send_file(
        image_io,
        as_attachment=True,
        download_name=filename,
        mimetype='image/png'
    )

@app.route('/decrypt', methods=['GET', 'POST'])
def decrypt():
    if request.method == 'POST':
        image = request.files.get('image')
        password = request.form.get('password')
        image_id = request.form.get('image_id')

        if not image or not password or not image_id:
            return render_template('decrypt.html', result="All fields are required.")

        image_bytes = image.read()
        result = decrypt_message(image_bytes, password, image_id)
        return render_template('decrypt.html', result=result)

    return render_template('decrypt.html')

if __name__ == '__main__':
    app.run(debug=True)