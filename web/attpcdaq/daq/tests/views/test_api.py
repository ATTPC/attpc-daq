from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from unittest.mock import patch, call
from datetime import datetime
import json
import tempfile
import logging

from .helpers import RequiresLoginTestMixin, NeedsExperimentTestMixin, ManySourcesTestCaseBase
from ...models import ECCServer, DataRouter, DataSource, RunMetadata, Experiment, Observable, Measurement
from ... import views
from ...views import UpdateRunMetadataView
from ...forms import RunMetadataForm


class RefreshStateAllViewTestCase(RequiresLoginTestMixin, NeedsExperimentTestMixin, ManySourcesTestCaseBase):
    def setUp(self):
        super().setUp()
        self.view_name = 'daq/source_refresh_state_all'

    def test_post(self):
        self.client.force_login(self.user)
        resp = self.client.post(reverse(self.view_name))
        self.assertEqual(resp.status_code, 405)

    def test_good_request(self):
        self.client.force_login(self.user)
        for ecc in self.ecc_servers:
            ecc.state = ECCServer.RUNNING
            ecc.save()

        resp = self.client.get(reverse(self.view_name))
        self.assertEqual(resp.resolver_match.func, views.refresh_state_all)

        response_json = resp.json()
        self.assertEqual(response_json['overall_state'], ECCServer.RUNNING)
        self.assertEqual(response_json['overall_state_name'], ECCServer.STATE_DICT[ECCServer.RUNNING])

        for res in response_json['ecc_server_status_list']:
            pk = int(res['pk'])
            ecc_server = ECCServer.objects.get(pk=pk)
            self.assertEqual(res['state'], ECCServer.RUNNING)
            self.assertEqual(res['state_name'], ecc_server.get_state_display())
            self.assertEqual(res['transitioning'], ecc_server.is_transitioning)
            self.assertTrue(res['success'])
            self.assertEqual(res['error_message'], '')

        for res in response_json['data_router_status_list']:
            pk = int(res['pk'])
            router = DataRouter.objects.get(pk=pk)
            self.assertEqual(res['is_online'], router.is_online)
            self.assertEqual(res['is_clean'], router.staging_directory_is_clean)
            self.assertTrue(res['success'])

    def test_response_contains_run_info(self):
        self.client.force_login(self.user)

        for ecc_server in self.ecc_servers:
            ecc_server.state = ECCServer.RUNNING
            ecc_server.save()

        run0 = RunMetadata.objects.create(run_number=0,
                                          experiment=self.experiment,
                                          start_datetime=datetime.now())

        resp = self.client.get(reverse(self.view_name))

        resp_json = resp.json()
        self.assertEqual(resp_json['run_number'], run0.run_number)
        self.assertEqual(resp_json['start_time'], run0.start_datetime.strftime('%b %d %Y, %H:%M:%S'))  # This is perhaps not the best
        self.assertEqual(resp_json['run_duration'], run0.duration_string)

    def test_ecc_servers_only_for_this_experiment(self):
        self.client.force_login(self.user)

        other_expt = Experiment.objects.create(name='Other')
        other_ecc = ECCServer.objects.create(
            name='Other ecc',
            ip_address='123.123.123.123',
            experiment=other_expt,
        )

        resp = self.client.get(reverse(self.view_name))
        self.assertNotIn(other_ecc.pk, [int(e['pk']) for e in resp.json()['ecc_server_status_list']])

    def test_data_routers_only_for_this_experiment(self):
        self.client.force_login(self.user)

        other_expt = Experiment.objects.create(name='Other')
        other_router = DataRouter.objects.create(
            name='Other router',
            ip_address='123.123.123.123',
            experiment=other_expt,
        )

        resp = self.client.get(reverse(self.view_name))
        self.assertNotIn(other_router.pk, [int(e['pk']) for e in resp.json()['data_router_status_list']])


class SourceChangeStateTestCase(RequiresLoginTestMixin, NeedsExperimentTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.view_name = 'daq/source_change_state'
        self.user = User.objects.create(
            username='test',
            password='test1234',
        )
        self.experiment = Experiment.objects.create(name='experiment', is_active=True)
        self.ecc = ECCServer.objects.create(
            name='test ecc',
            ip_address='123.123.123.123',
            experiment=self.experiment,

        )
        self.datarouter = DataRouter.objects.create(
            name='router',
            ip_address='123.123.123.123',
            experiment=self.experiment,
        )
        self.datasource = DataSource.objects.create(
            ecc_server=self.ecc,
            data_router=self.datarouter,
        )

    def test_all_transitions_work(self):
        self.client.force_login(self.user)

        self.ecc.state = ECCServer.IDLE
        self.ecc.save()

        state_list = (
            ECCServer.DESCRIBED,
            ECCServer.PREPARED,
            ECCServer.READY,
            ECCServer.RUNNING,
            ECCServer.READY,
            ECCServer.RESET,
            ECCServer.RESET,
            ECCServer.RESET,
        )

        with patch('attpcdaq.daq.views.api.eccserver_change_state_task.delay') as mock_task_delay:
            for transition_number in state_list:
                if transition_number == ECCServer.RESET:
                    target_state = self.ecc.state - 1
                else:
                    target_state = transition_number

                resp = self.client.post(reverse(self.view_name), {'pk': self.ecc.pk, 'target_state': transition_number})
                self.ecc.refresh_from_db()

                self.assertEqual(resp.status_code, 200)
                mock_task_delay.assert_called_once_with(self.ecc.pk, target_state)

                self.assertTrue(self.ecc.is_transitioning)

                mock_task_delay.reset_mock()

                # Prepare for the next iteration since they won't actually transition
                self.ecc.state = target_state
                self.ecc.is_transitioning = False
                self.ecc.save()


@patch('attpcdaq.daq.views.api.eccserver_change_state_task.delay')
class SourceChangeStateAllTestCase(RequiresLoginTestMixin, NeedsExperimentTestMixin, ManySourcesTestCaseBase):
    def setUp(self):
        super().setUp()
        self.view_name = 'daq/source_change_state_all'

    def test_get(self, _):
        self.client.force_login(self.user)
        resp = self.client.get(reverse(self.view_name))
        self.assertEqual(resp.status_code, 405)

    def test_with_no_runs(self, mock_task_delay):
        self.client.force_login(self.user)

        resp = self.client.post(reverse(self.view_name), {'target_state': ECCServer.DESCRIBED})
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.json()['run_number'])

    def test_only_affects_current_experiment(self, mock_task_delay):
        self.client.force_login(self.user)

        new_expt = Experiment.objects.create(name='new experiment')
        new_ecc = ECCServer.objects.create(
            name='new ecc',
            ip_address='123.123.123.123',
            experiment=new_expt,
        )
        new_router = DataRouter.objects.create(
            name='new router',
            ip_address='123.123.123.123',
            experiment=new_expt,
        )
        DataSource.objects.create(
            ecc_server=new_ecc,
            data_router=new_router,
        )

        resp = self.client.post(reverse(self.view_name), {'target_state': ECCServer.DESCRIBED})

        used_pks = [c[0][0] for c in mock_task_delay.call_args_list]
        self.assertNotIn(new_ecc.pk, used_pks)

    def test_all_transitions_work(self, mock_task_delay):
        self.client.force_login(self.user)

        ECCServer.objects.all().update(state=ECCServer.IDLE)

        state_list = (
            ECCServer.DESCRIBED,
            ECCServer.PREPARED,
            ECCServer.READY,
            ECCServer.RUNNING,
            ECCServer.READY,
            ECCServer.RESET,
            ECCServer.RESET,
            ECCServer.RESET,
        )

        with patch('attpcdaq.daq.views.api.organize_files_all_task.delay') as mock_organize:
            with patch('attpcdaq.daq.views.api.backup_config_files_all_task.delay') as mock_backup:
                for transition_number in state_list:
                    if transition_number == ECCServer.RESET:
                        target_state = ECCServer.objects.first().state - 1
                    else:
                        target_state = transition_number

                    resp = self.client.post(reverse(self.view_name), {'target_state': transition_number})

                    self.assertEqual(resp.status_code, 200)
                    expected_calls = [call(e.pk, target_state) for e in ECCServer.objects.all()]
                    mock_task_delay.assert_has_calls(expected_calls)

                    self.assertFalse(ECCServer.objects.filter(is_transitioning=False).exists())

                    mock_task_delay.reset_mock()

                    # Prepare for the next iteration since they won't actually transition
                    ECCServer.objects.all().update(state=target_state, is_transitioning=False)

    def test_start(self, mock_change_state_task_delay):
        self.client.force_login(self.user)
        ECCServer.objects.all().update(state=ECCServer.READY)

        resp = self.client.post(reverse(self.view_name), {'target_state': ECCServer.RUNNING})

        self.assertEqual(resp.status_code, 200)

        self.experiment.refresh_from_db()
        self.assertTrue(self.experiment.is_running)

    def test_stop(self, mock_change_state_task_delay):
        self.client.force_login(self.user)
        ECCServer.objects.all().update(state=ECCServer.RUNNING)
        self.experiment.start_run()

        with patch('attpcdaq.daq.views.api.organize_files_all_task.delay') as mock_organize:
            with patch('attpcdaq.daq.views.api.backup_config_files_all_task.delay') as mock_backup:
                resp = self.client.post(reverse(self.view_name), {'target_state': ECCServer.READY})

                self.assertEqual(resp.status_code, 200)

                mock_organize.assert_called_once_with(self.experiment.pk, self.experiment.latest_run.pk)
                mock_backup.assert_called_once_with(self.experiment.pk, self.experiment.latest_run.pk)


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


class ListRunMetadataViewTestCase(RequiresLoginTestMixin, NeedsExperimentTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.view_name = 'daq/run_list'

        self.user = User.objects.create(username='testUser', password='test1234')
        self.experiment = Experiment.objects.create(name='Test experiment', is_active=True)

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
        newexpt = Experiment.objects.create(name='Another experiment')
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


class SetObservableOrderingTestCase(RequiresLoginTestMixin, NeedsExperimentTestMixin, TestCase):
    def setUp(self):
        self.view_name = 'daq/set_observable_ordering'
        self.user = User.objects.create(
            username='test',
            password='test1234',
        )
        self.experiment = Experiment.objects.create(
            name='Test experiment',
            is_active=True,
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


class ListEccServerViewTestCase(RequiresLoginTestMixin, NeedsExperimentTestMixin, TestCase):
    def setUp(self):
        self.experiment = Experiment.objects.create(name='Test', is_active=True)

        self.user = User.objects.create(
            username='User',
            password='test1234',
        )

        self.view_name = 'daq/ecc_server_list'

    def test_excludes_other_experiments(self):
        ECCServer.objects.create(
            name='good ecc',
            ip_address='123.123.123.123',
            experiment=self.experiment,
        )

        other_experiment = Experiment.objects.create(name='Other')
        bad_ecc = ECCServer.objects.create(
            name='bad ecc',
            ip_address='122.122.122.122',
            experiment=other_experiment,
        )

        self.client.force_login(self.user)
        resp = self.client.get(reverse(self.view_name))
        self.assertNotIn(bad_ecc, resp.context['eccserver_list'])


class ListDataRoutersViewTestCase(RequiresLoginTestMixin, NeedsExperimentTestMixin, TestCase):
    def setUp(self):
        self.experiment = Experiment.objects.create(name='Test', is_active=True)

        self.user = User.objects.create(
            username='User',
            password='test1234',
        )

        self.view_name = 'daq/data_router_list'

    def test_excludes_other_experiments(self):
        DataRouter.objects.create(
            name='good router',
            ip_address='123.123.123.123',
            experiment=self.experiment,
        )

        other_experiment = Experiment.objects.create(name='Other')
        bad_router = DataRouter.objects.create(
            name='bad router',
            ip_address='122.122.122.122',
            experiment=other_experiment,
        )

        self.client.force_login(self.user)
        resp = self.client.get(reverse(self.view_name))
        self.assertNotIn(bad_router, resp.context['datarouter_list'])


class ListDataSourcesViewTestCase(RequiresLoginTestMixin, NeedsExperimentTestMixin, TestCase):
    def setUp(self):
        self.experiment = Experiment.objects.create(name='Test', is_active=True)

        self.user = User.objects.create(
            username='User',
            password='test1234',
        )

        self.view_name = 'daq/data_source_list'

    def test_excludes_other_experiments(self):
        good_ecc = ECCServer.objects.create(
            name='good ecc',
            ip_address='123.123.123.123',
            experiment=self.experiment,
        )
        good_router = DataRouter.objects.create(
            name='good router',
            ip_address='123.123.123.123',
            experiment=self.experiment,
        )
        DataSource.objects.create(
            name='Good source',
            ecc_server=good_ecc,
            data_router=good_router,
        )

        other_experiment = Experiment.objects.create(name='Other')
        bad_ecc = ECCServer.objects.create(
            name='bad ecc',
            ip_address='122.122.122.122',
            experiment=other_experiment,
        )
        bad_router = DataRouter.objects.create(
            name='bad router',
            ip_address='122.122.122.122',
            experiment=other_experiment,
        )
        bad_source = DataSource.objects.create(
            name='Bad source',
            ecc_server=bad_ecc,
            data_router=bad_router,
        )

        self.client.force_login(self.user)
        resp = self.client.get(reverse(self.view_name))
        self.assertNotIn(bad_source, resp.context['datasource_list'])
