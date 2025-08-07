import unittest
from unittest.mock import patch, MagicMock
from app import app, encrypt_message, decrypt_message
from io import BytesIO
from PIL import Image

class FlaskAppTestCase(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

        # Create a dummy image in memory
        self.test_image = Image.new('RGB', (100, 100), color='white')
        self.image_io = BytesIO()
        self.test_image.save(self.image_io, format='PNG')
        self.image_io.seek(0)

    def test_homepage(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_encrypt_page_get(self):
        response = self.client.get('/encrypt')
        self.assertEqual(response.status_code, 200)

    @patch('app.cursor')
    def test_encrypt_post_success(self, mock_cursor):
        mock_cursor.execute = MagicMock()
        mock_cursor.fetchone = MagicMock()
        data = {
            'image': (BytesIO(self.image_io.getvalue()), 'test.png'),
            'message': 'Hello, World!',
            'password': 'testpass'
        }
        response = self.client.post('/encrypt', data=data, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Your Image ID:', response.data)

    @patch('app.cursor')
    def test_encrypt_post_missing_fields(self, mock_cursor):
        data = {
            'image': (BytesIO(self.image_io.getvalue()), 'test.png'),
            'message': '',
            'password': 'testpass'
        }
        response = self.client.post('/encrypt', data=data, content_type='multipart/form-data')
        self.assertIn(b'All fields are required.', response.data)

    def test_decrypt_page_get(self):
        response = self.client.get('/decrypt')
        self.assertEqual(response.status_code, 200)

    @patch('app.cursor')
    def test_encrypt_and_decrypt_logic(self, mock_cursor):
        # Simulate encryption
        encrypted_io, _, error = encrypt_message(BytesIO(self.image_io.getvalue()), 'Secret Message')
        self.assertIsNone(error)
        image_bytes = encrypted_io.getvalue()

        # Mock DB password check
        mock_cursor.execute = MagicMock()
        mock_cursor.fetchone = MagicMock(return_value=('testpass',))

        # Simulate correct password decryption
        result = decrypt_message(image_bytes, 'testpass', 'some_id')
        self.assertEqual(result, 'Secret Message')

    @patch('app.cursor')
    def test_decrypt_wrong_password(self, mock_cursor):
        encrypted_io, _, _ = encrypt_message(BytesIO(self.image_io.getvalue()), 'Hidden')
        image_bytes = encrypted_io.getvalue()

        # Wrong password scenario
        mock_cursor.execute = MagicMock()
        mock_cursor.fetchone = MagicMock(return_value=('correctpass',))

        result = decrypt_message(image_bytes, 'wrongpass', 'some_id')
        self.assertEqual(result, 'YOU ARE NOT AUTHORIZED!')

if __name__ == '__main__':
    unittest.main()
