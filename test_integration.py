import re
from app import app
from PIL import Image
from io import BytesIO
import unittest
from unittest.mock import patch, MagicMock

class IntegrationTest(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.test_message = "Top Secret Message"
        self.test_password = "integration123"

        # Create an in-memory test image
        image = Image.new('RGB', (100, 100), color='white')
        self.image_io = BytesIO()
        image.save(self.image_io, format='PNG')
        self.image_io.seek(0)

    @patch('app.cursor')
    def test_full_encrypt_decrypt_cycle(self, mock_cursor):
        # Patch DB methods
        mock_cursor.execute = MagicMock()
        mock_cursor.fetchone = MagicMock(return_value=(self.test_password,))

        # Step 1: Encrypt
        encrypt_data = {
            'image': (BytesIO(self.image_io.getvalue()), 'test_image.png'),
            'message': self.test_message,
            'password': self.test_password
        }
        response = self.client.post('/encrypt', data=encrypt_data, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 200)

        # Step 2: Extract image_id from HTML
        html = response.data.decode('utf-8')
        match = re.search(r'<span id="imageID">([a-f0-9-]+)</span>', html)
        self.assertIsNotNone(match)
        image_id = match.group(1)

        # Step 3: Download the encrypted image
        download_response = self.client.get(f'/download/{image_id}')
        self.assertEqual(download_response.status_code, 200)
        encrypted_image_bytes = download_response.data

        # Step 4: Decrypt
        decrypt_data = {
            'image': (BytesIO(encrypted_image_bytes), 'encrypted.png'),
            'password': self.test_password,
            'image_id': image_id
        }
        decrypt_response = self.client.post('/decrypt', data=decrypt_data, content_type='multipart/form-data')
        self.assertEqual(decrypt_response.status_code, 200)
        self.assertIn(self.test_message.encode('utf-8'), decrypt_response.data)

if __name__ == '__main__':
    unittest.main()
