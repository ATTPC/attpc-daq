from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from unittest.mock import patch
from datetime import datetime
import json
import tempfile
import logging

from .helpers import RequiresLoginTestMixin, ManySourcesTestCaseBase
from ...models import ECCServer, DataRouter, RunMetadata, Experiment, Observable, Measurement
from ... import views
from ...views import UpdateRunMetadataView
from ...forms import RunMetadataForm


class AddDataSourceViewTestCase(RequiresLoginTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.view_name = 'daq/add_source'


class UpdateDataSourceViewTestCase(RequiresLoginTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.view_name = 'daq/update_source'

    def test_no_login(self, *args, **kwargs):
        super().test_no_login(rev_args=(1,))


class RemoveDataSourceViewTestCase(RequiresLoginTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.view_name = 'daq/remove_source'

    def test_no_login(self, *args, **kwargs):
        super().test_no_login(rev_args=(1,))


class ListRunMetadataViewTestCase(RequiresLoginTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.view_name = 'daq/run_list'

        self.user = User.objects.create(username='testUser', password='test1234')
        self.experiment = Experiment.objects.create(name='Test experiment', user=self.user)

        self.runs = []
        for i in (0, 3, 1, 2, 5, 4, 7, 9, 8):  # In a random order to test sorting
            r = RunMetadata.objects.create(run_number=i,
                                           start_datetime=datetime.now(),
                                           stop_datetime=datetime.now(),
                                           experiment=self.experiment)
            self.runs.append(r)

    def test_runs_are_sorted_by_run_number(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse(self.view_name))
        self.assertEqual(resp.status_code, 200)

        run_list = resp.context['runmetadata_list']
        run_nums = [run.run_number for run in run_list]
        self.assertEqual(sorted(run_nums), run_nums)

    def test_runs_are_only_for_this_experiment(self):
        self.client.force_login(self.user)

        newuser = User.objects.create(username='newExperiment', password='new12345')
        newexpt = Experiment.objects.create(name='Another experiment', user=newuser)
        newrun = RunMetadata.objects.create(run_number=0,
                                            start_datetime=datetime.now(),
                                            stop_datetime=datetime.now(),
                                            experiment=newexpt)

        resp = self.client.get(reverse(self.view_name))
        self.assertEqual(resp.status_code, 200)

        run_list = resp.context['runmetadata_list']
        self.assertNotIn(newrun, run_list)


class UploadDataSourceListTestCase(RequiresLoginTestMixin, ManySourcesTestCaseBase):
    def setUp(self):
        super().setUp()
        self.view_name = 'daq/upload_datasource_list'

    def _get_data(self):
        download_resp = self.client.get(reverse('daq/download_datasource_list'))

        data = download_resp.json()
        for node in data:
            if 'pk' in node:
                del node['pk']

        return data

    def test_upload_when_db_list_full(self):
        self.client.force_login(self.user)

        data = self._get_data()

        with tempfile.NamedTemporaryFile(mode='w+') as fp:
            json.dump(data, fp)
            fp.seek(0)
            upload_resp = self.client.post(reverse(self.view_name), data={'data_source_list': fp})

        data_new = self._get_data()
        self.assertEqual(data, data_new)


class UpdateRunMetadataViewTestCase(RequiresLoginTestMixin, TestCase):
    def setUp(self):
        self.view_name = 'daq/update_run_metadata'

        self.user = User.objects.create(
            username='test',
            password='test1234',
        )
        self.experiment = Experiment.objects.create(
            name='Test experiment',
            user=self.user,
        )
        self.observable = Observable.objects.create(
            name='Observable quantity',
            value_type=Observable.INTEGER,
            experiment=self.experiment,
        )

    def test_no_login(self, *args, **kwargs):
        super().test_no_login(rev_args=(1,))

    def make_run(self):
        return RunMetadata.objects.create(
            experiment=self.experiment,
            run_number=self.experiment.next_run_number,
            start_datetime=datetime(2016, 1, 1, self.experiment.next_run_number, 0, 0),
            stop_datetime=datetime(2016, 1, 1, self.experiment.next_run_number + 1, 0, 0),
        )

    def test_prepopulate(self):
        self.client.force_login(self.user)

        run0 = self.make_run()

        measurement0 = Measurement(
            observable=self.observable,
            run_metadata=run0,
        )
        measurement0.value = 5
        measurement0.save()

        run1 = self.make_run()

        resp = self.client.get(reverse(self.view_name, args=(run1.pk,)), data={'prepopulate': True})
        self.assertEqual(resp.status_code, 200)

        # Build expected `initial` dictionary.
        # Using values from run0, fill fields that *should* be prepopulated.
        expected_initial = {f: getattr(run0, f)
                            for f in RunMetadataForm.Meta.fields
                            if f not in UpdateRunMetadataView.automatic_fields}

        # Using values from run1, fill fields that *should not* be prepopulated.
        expected_initial.update({f: getattr(run1, f) for f in UpdateRunMetadataView.automatic_fields})

        # Fill in measurement-related fields using run0, as these should be prepopulated
        expected_initial[measurement0.observable.name] = measurement0.value

        form = resp.context['form']
        self.assertEqual(form.initial, expected_initial)

    def test_prepopulate_fails_without_previous_run(self):
        self.client.force_login(self.user)

        run0 = self.make_run()

        with self.assertLogs(level=logging.ERROR):
            resp = self.client.get(reverse(self.view_name, args=(run0.pk,)), data={'prepopulate': True})

        self.assertEqual(resp.status_code, 200)  # Even though it won't prepopulate, it should still work


class SetObservableOrderingTestCase(RequiresLoginTestMixin, TestCase):
    def setUp(self):
        self.view_name = 'daq/set_observable_ordering'
        self.user = User.objects.create(
            username='test',
            password='test1234',
        )
        self.experiment = Experiment.objects.create(
            name='Test experiment',
            user=self.user,
        )
        for i in range(20):
            Observable.objects.create(
                name='Observable{}'.format(i),
                value_type=Observable.FLOAT,
                experiment=self.experiment,
            )

    def test_set_ordering(self):
        self.client.force_login(self.user)

        new_order = [o.pk for o in Observable.objects.filter(experiment=self.experiment).order_by('-pk')]
        resp = self.client.post(reverse(self.view_name), data=json.dumps({'new_order': new_order}),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {'success': True})

        order_after = [o.pk for o in Observable.objects.filter(experiment=self.experiment).order_by('order')]
        self.assertEqual(order_after, new_order)
