from django.test import TestCase
from django.urls import reverse


class ProjectApiTests(TestCase):
    def test_create_project_endpoint(self):
        response = self.client.post(
            reverse('api:project-list-create'),
            {'prompt': 'Une histoire courte pour tester l’API'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn('id', response.json())
        self.assertEqual(response.json()['prompt'], 'Une histoire courte pour tester l’API')
