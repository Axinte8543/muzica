from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from users.tasks import scan_avatar_object
from users.models import UserPrivacySettings, AvatarScanStatus


@override_settings(CLAMAV_HOST='localhost', AVATAR_SCAN_REQUIRED=True)
class ScanAvatarTaskTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='scanuser', password='pw')
        self.profile = UserPrivacySettings.objects.create(user=self.user)

    @patch('boto3.client')
    @patch('socket.create_connection')
    def test_scan_avatar_clean(self, mock_socket, mock_boto):
                        
        mock_body = MagicMock()
        mock_body.read.return_value = b'cleancontent'
        mock_boto.return_value.get_object.return_value = {'Body': mock_body}

                                  
        sock = MagicMock()
        sock.recv.return_value = b'OK\n'
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = sock
        mock_socket.return_value = mock_ctx

        ok, msg = scan_avatar_object.run('bucket', 'key', self.user.id)
        self.profile.refresh_from_db()
        self.assertTrue(ok)
        self.assertEqual(self.profile.avatar_scan_status, AvatarScanStatus.CLEAN)

    @patch('boto3.client')
    @patch('socket.create_connection')
    def test_scan_avatar_infected(self, mock_socket, mock_boto):
        mock_body = MagicMock()
        mock_body.read.return_value = b'infectedcontent'
        mock_boto.return_value.get_object.return_value = {'Body': mock_body}

        sock = MagicMock()
        sock.recv.return_value = b'Trojan.Fake FOUND\n'
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = sock
        mock_socket.return_value = mock_ctx

        ok, msg = scan_avatar_object.run('bucket', 'key', self.user.id)
        self.profile.refresh_from_db()
        self.assertFalse(ok)
        self.assertEqual(self.profile.avatar_scan_status, AvatarScanStatus.REJECTED)
