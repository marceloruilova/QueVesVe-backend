from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from users.models.custom_user_models import CustomUser
from videos.models import Video
from reports.models import ContentReport, CopyrightReport


def make_test_user(username, email, password='Pass123!'):
    return CustomUser.objects.create_user(username=username, email=email, password=password)


def auth_header(user):
    refresh = RefreshToken.for_user(user)
    return f'Bearer {refresh.access_token}'


# ---------------------------------------------------------------------------
# ReportVideoView  →  POST /videos/<videoid>/report/
# ---------------------------------------------------------------------------

class ReportVideoViewTest(APITestCase):

    def setUp(self):
        self.user = make_test_user('reporter', 'reporter@example.com')
        self.client.credentials(HTTP_AUTHORIZATION=auth_header(self.user))

        self.video_owner = make_test_user('owner', 'owner@example.com')
        self.video = Video.objects.create(
            user=self.video_owner,
            description='Test video',
            tags='test',
            music='test music',
        )
        self.url = reverse('report_video', kwargs={'videoid': self.video.pk})
        self.valid_payload = {'reason': 'spam'}

    def test_successful_report_returns_201(self):
        response = self.client.post(self.url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            ContentReport.objects.filter(reporter=self.user, video=self.video).exists()
        )

    def test_nonexistent_video_returns_404(self):
        url = reverse('report_video', kwargs={'videoid': 99999})
        response = self.client.post(url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_duplicate_report_returns_400(self):
        self.client.post(self.url, self.valid_payload, format='json')
        response = self.client.post(self.url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            ContentReport.objects.filter(reporter=self.user, video=self.video).count(), 1
        )

    def test_unauthenticated_request_returns_401(self):
        self.client.credentials()
        response = self.client.post(self.url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_reason_returns_400(self):
        payload = {'reason': 'not_a_valid_reason'}
        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('reason', response.data)

    def test_missing_reason_returns_400(self):
        response = self.client.post(self.url, {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('reason', response.data)

    def test_report_with_optional_details_is_saved(self):
        payload = {'reason': 'harassment', 'details': 'Este video me acosa.'}
        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        report = ContentReport.objects.get(reporter=self.user, video=self.video)
        self.assertEqual(report.details, 'Este video me acosa.')


# ---------------------------------------------------------------------------
# CopyrightReportView  →  POST /reports/copyright/
# ---------------------------------------------------------------------------

class CopyrightReportViewTest(APITestCase):

    def setUp(self):
        self.user = make_test_user('copyrighter', 'copy@example.com')
        self.client.credentials(HTTP_AUTHORIZATION=auth_header(self.user))

        self.video_owner = make_test_user('vowner', 'vowner@example.com')
        self.video = Video.objects.create(
            user=self.video_owner,
            description='Video with copyrighted content',
            tags='',
            music='',
        )
        self.url = reverse('report_copyright')
        self.valid_payload = {
            'reporter_name': 'Jane Doe',
            'reporter_email': 'jane@example.com',
            'video': self.video.pk,
            'work_description': 'My original song was used without permission.',
            'original_url': 'https://example.com/my-original-song',
            'good_faith_statement': True,
            'accuracy_statement': True,
        }

    def test_successful_copyright_report_returns_201(self):
        response = self.client.post(self.url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CopyrightReport.objects.count(), 1)
        report = CopyrightReport.objects.first()
        self.assertEqual(report.reporter_email, 'jane@example.com')
        self.assertEqual(report.video, self.video)

    def test_good_faith_false_returns_400(self):
        payload = {**self.valid_payload, 'good_faith_statement': False}
        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('good_faith_statement', response.data)

    def test_good_faith_absent_returns_400(self):
        payload = {k: v for k, v in self.valid_payload.items() if k != 'good_faith_statement'}
        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_accuracy_false_returns_400(self):
        payload = {**self.valid_payload, 'accuracy_statement': False}
        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('accuracy_statement', response.data)

    def test_unauthenticated_request_returns_401(self):
        self.client.credentials()
        response = self.client.post(self.url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_email_returns_400(self):
        payload = {**self.valid_payload, 'reporter_email': 'not-an-email'}
        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('reporter_email', response.data)
