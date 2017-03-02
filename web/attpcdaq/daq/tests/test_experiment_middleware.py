from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from ..models import Experiment, ECCServer


class CurrentExperimentMiddlewareTestCase(TestCase):
    def setUp(self):
        self.experiment = Experiment.objects.create(name='Experiment')
        self.ecc = ECCServer.objects.create(
            name='ecc0',
            ip_address='123.123.123.123',
            experiment=self.experiment,
        )
        self.user = User.objects.create(
            username='user',
            password='user1234',
        )
        self.client.force_login(self.user)
        self.request_url = reverse('daq/status')

    def test_gets_experiment_from_database(self):
        self.experiment.is_active = True
        self.experiment.save()

        resp = self.client.get(self.request_url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['experiment'], self.experiment)

    def test_redirects_when_no_experiment_is_active(self):
        resp = self.client.get(self.request_url, follow=True)
        self.assertEqual(resp.redirect_chain[-1][0], reverse('daq/choose_experiment'))
