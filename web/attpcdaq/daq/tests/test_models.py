from django.test import TestCase
from unittest.mock import patch
from .utilities import FakeResponseState, FakeResponseText
from ..models import DataSource, ECCServer, DataRouter, ConfigId, Experiment, RunMetadata, Observable, Measurement
from ..models import ECCError
import xml.etree.ElementTree as ET
import os
from itertools import permutations, product
from datetime import datetime


class FakeTransitionResult(object):
    def __init__(self, error_code, error_message):
        self.ErrorCode = error_code
        self.ErrorMessage = error_message


class ConfigIdModelTestCase(TestCase):
    def setUp(self):
        self.describe_name = 'describe_name'
        self.prepare_name = 'prepare_name'
        self.configure_name = 'configure_name'
        self.config = ConfigId(describe=self.describe_name,
                               prepare=self.prepare_name,
                               configure=self.configure_name)

        root = ET.Element('ConfigId')
        describe_node = ET.SubElement(root, 'SubConfigId', attrib={'type': 'describe'})
        describe_node.text = self.describe_name
        prepare_node = ET.SubElement(root, 'SubConfigId', attrib={'type': 'prepare'})
        prepare_node.text = self.prepare_name
        configure_node = ET.SubElement(root, 'SubConfigId', attrib={'type': 'configure'})
        configure_node.text = self.configure_name
        self.xml_root = root

    def test_str(self):
        s = str(self.config)
        self.assertEqual(s, '{}/{}/{}'.format(self.describe_name, self.prepare_name, self.configure_name))

    def test_as_xml(self):
        xml = self.config.as_xml()
        root = ET.fromstring(xml)
        self.assertEqual(root.tag, 'ConfigId')
        for node in root:
            self.assertEqual(node.tag, 'SubConfigId')

            node_type = node.get('type')
            if node_type == 'describe':
                self.assertEqual(node.text, self.describe_name)
            elif node_type == 'prepare':
                self.assertEqual(node.text, self.prepare_name)
            elif node_type == 'configure':
                self.assertEqual(node.text, self.configure_name)
            else:
                self.fail('Unknown node type: {}'.format(node_type))

            self.assertEqual(len(node), 0, msg='SubConfigId node should have 0 children.')

    def test_from_xml_valid(self):
        new_config = ConfigId.from_xml(self.xml_root)

        self.assertEqual(new_config.describe, self.describe_name)
        self.assertEqual(new_config.prepare, self.prepare_name)
        self.assertEqual(new_config.configure, self.configure_name)

    def test_from_xml_with_string(self):
        xml_string = ET.tostring(self.xml_root)

        new_config = ConfigId.from_xml(xml_string)

        self.assertEqual(new_config.describe, self.describe_name)
        self.assertEqual(new_config.prepare, self.prepare_name)
        self.assertEqual(new_config.configure, self.configure_name)

    def test_from_xml_with_bad_root_node(self):
        self.xml_root.tag = 'NotAValidTag'
        self.assertRaisesRegex(ValueError, 'Not a ConfigId node', ConfigId.from_xml, self.xml_root)

    def test_from_xml_with_bad_type(self):
        self.xml_root[0].set('type', 'BadType')
        self.assertRaisesRegex(ValueError, 'Unknown or missing config type: BadType', ConfigId.from_xml, self.xml_root)


class ECCServerModelTestCase(TestCase):
    def setUp(self):
        self.name = 'ECC'
        self.ip_address = '123.45.67.8'
        self.port = '1234'
        self.experiment = Experiment.objects.create(
            name='Test',
        )
        self.selected_config = ConfigId.objects.create(
            describe='describe',
            prepare='prepare',
            configure='configure'
        )
        self.ecc_server = ECCServer.objects.create(
            name=self.name,
            ip_address=self.ip_address,
            port=self.port,
            selected_config=self.selected_config,
            experiment=self.experiment,
        )

    def test_ecc_url(self):
        ecc_url = self.ecc_server.ecc_url
        expected = 'http://{}:{}/'.format(self.ip_address, self.port)
        self.assertEqual(ecc_url, expected)

    def test_config_paths(self):
        expected_root = '/Volumes/configs'
        expected = (
            os.path.join(expected_root, 'describe-describe.xcfg'),
            os.path.join(expected_root, 'prepare-prepare.xcfg'),
            os.path.join(expected_root, 'configure-configure.xcfg'),
        )
        result = self.ecc_server.config_file_paths()

        self.assertEqual(result, expected)

    def data_link_xml_test_impl(self):
        xml_string = self.ecc_server.get_data_link_xml_from_clients()
        root = ET.fromstring(xml_string)

        self.assertEqual(root.tag, 'DataLinkSet')

        data_link_nodes = root.findall('DataLink')

        self.assertEqual(len(data_link_nodes), DataSource.objects.count())

        for link in data_link_nodes:
            ds_name = link.find('DataSender').attrib['id']
            datasource = DataSource.objects.get(name=ds_name)
            check_data_link_xml_helper(self, datasource, link)

    def test_get_data_link_xml_one_source(self):
        data_router = DataRouter.objects.create(
            name='DataRouter0',
            ip_address=self.ip_address,
            experiment=self.experiment,
        )
        datasource = DataSource.objects.create(
            name='CoBo[0]',
            ecc_server=self.ecc_server,
            data_router=data_router,
        )

        self.data_link_xml_test_impl()

    def test_get_data_link_xml_many_sources_one_ecc(self):
        for i in range(10):
            router = DataRouter.objects.create(
                name='DataRouter{:d}'.format(i),
                ip_address='123.456.789.{:d}'.format(i),
                experiment=self.experiment,
            )
            DataSource.objects.create(
                name='CoBo[{:d}]'.format(i),
                ecc_server=self.ecc_server,
                data_router=router,
            )

        self.data_link_xml_test_impl()

    @patch('attpcdaq.daq.models.EccClient')
    def test_get_transition_too_many_steps(self, mock_client):
        mock_instance = mock_client()
        for initial_state, final_state in permutations(ECCServer.STATE_DICT.keys(), 2):
            if final_state - initial_state not in (1, -1):
                self.assertRaisesRegex(ValueError, 'Can only transition one step at a time\.',
                                       self.ecc_server._get_transition, mock_instance,
                                       initial_state, final_state)

    @patch('attpcdaq.daq.models.EccClient')
    def test_get_transition_same_state(self, mock_client):
        mock_instance = mock_client()
        for state in ECCServer.STATE_DICT.keys():
            self.assertRaisesRegex(ValueError, 'No transition needed.', self.ecc_server._get_transition,
                                   mock_instance, state, state)

    def test_refresh_configs(self):
        config_names = ['A', 'B', 'C']
        configs = [ConfigId(describe=a, prepare=b, configure=c)
                   for a, b, c in permutations(config_names, 3)]
        configs_xml = '<ConfigIdList>' + ''.join((c.as_xml() for c in configs)) + '</ConfigIdList>'

        def return_side_effect():
            class FakeResult(object):
                Text = configs_xml
            return FakeResult()

        with patch('attpcdaq.daq.models.EccClient') as mock_client:
            instance = mock_client.return_value
            instance.GetConfigIDs.side_effect = return_side_effect

            self.ecc_server.refresh_configs()

            instance.GetConfigIDs.assert_called_once_with()

        for config in configs:
            self.assertTrue(ConfigId.objects.filter(describe=config.describe,
                                                    prepare=config.prepare,
                                                    configure=config.configure).exists())

    @patch('attpcdaq.daq.models.EccClient')
    def test_refresh_configs_does_not_duplicate_existing(self, mock_client):
        config_names = ['A', 'B', 'C']
        configs = [ConfigId(describe=a, prepare=b, configure=c)
                   for a, b, c in permutations(config_names, 3)]
        configs_xml = '<ConfigIdList>' + ''.join((c.as_xml() for c in configs)) + '</ConfigIdList>'

        mock_inst = mock_client.return_value
        mock_inst.GetConfigIDs.return_value = FakeResponseText(text=configs_xml)

        self.ecc_server.refresh_configs()
        self.ecc_server.refresh_configs()  # Call a second time to see if duplication occurs

        self.assertEqual(len(self.ecc_server.configid_set.all()), len(configs))

    @patch('attpcdaq.daq.models.EccClient')
    def test_refresh_configs_removes_outdated(self, mock_client):
        config_names = ['A', 'B', 'C']
        configs = [ConfigId(describe=a, prepare=b, configure=c)
                   for a, b, c in permutations(config_names, 3)]
        configs_xml = '<ConfigIdList>' + ''.join((c.as_xml() for c in configs)) + '</ConfigIdList>'

        mock_inst = mock_client.return_value
        mock_inst.GetConfigIDs.return_value = FakeResponseText(text=configs_xml)

        self.ecc_server.refresh_configs()  # Get the initial list

        # Remove a config and update the mock response
        removed_config = configs[0]
        del configs[0]
        configs_xml = '<ConfigIdList>' + ''.join((c.as_xml() for c in configs)) + '</ConfigIdList>'
        mock_inst.GetConfigIDs.return_value = FakeResponseText(text=configs_xml)

        self.ecc_server.refresh_configs()  # Now pull in the updated list

        self.assertFalse(
            self.ecc_server.configid_set.filter(
                describe=removed_config.describe,
                prepare=removed_config.prepare,
                configure=removed_config.configure
            ).exists(),
            msg='Removed config was still present in database.'
        )

    def test_refresh_state(self):
        for (state, trans) in product(ECCServer.STATE_DICT.keys(), [False, True]):
            with patch('attpcdaq.daq.models.EccClient') as mock_client:
                mock_inst = mock_client.return_value
                mock_inst.GetState.return_value = \
                    FakeResponseState(state=state, trans=trans)

                self.ecc_server.refresh_state()

                mock_inst.GetState.assert_called_once_with()

            self.assertEqual(self.ecc_server.state, state)
            self.assertEqual(self.ecc_server.is_transitioning, trans)

    def _transition_test_helper(self, trans_func_name, initial_state, final_state,
                                error_code=0, error_msg=""):
        with patch('attpcdaq.daq.models.EccClient') as mock_client:
            self.ecc_server.state = initial_state
            self.ecc_server.is_transitioning = False

            mock_instance = mock_client.return_value
            mock_trans_func = getattr(mock_instance, trans_func_name)
            mock_trans_func.return_value = FakeTransitionResult(error_code, error_msg)

            self.ecc_server.change_state(final_state)

            config_xml = self.ecc_server.selected_config.as_xml()
            datalink_xml = self.ecc_server.get_data_link_xml_from_clients()
            mock_trans_func.assert_called_once_with(config_xml, datalink_xml)

            self.assertTrue(self.ecc_server.is_transitioning)

    def test_change_state(self):
        self._transition_test_helper('Describe', ECCServer.IDLE, ECCServer.DESCRIBED)
        self._transition_test_helper('Undo', ECCServer.DESCRIBED, ECCServer.IDLE)

        self._transition_test_helper('Prepare', ECCServer.DESCRIBED, ECCServer.PREPARED)
        self._transition_test_helper('Undo', ECCServer.PREPARED, ECCServer.DESCRIBED)

        self._transition_test_helper('Configure', ECCServer.PREPARED, ECCServer.READY)
        self._transition_test_helper('Breakup', ECCServer.READY, ECCServer.PREPARED)

        self._transition_test_helper('Start', ECCServer.READY, ECCServer.RUNNING)
        self._transition_test_helper('Stop', ECCServer.RUNNING, ECCServer.READY)

    def test_change_state_with_error(self):
        error_code = 1
        error_msg = 'An error occurred'

        with self.assertRaisesRegex(ECCError, '.*' + error_msg):
            self._transition_test_helper('Describe', ECCServer.IDLE, ECCServer.DESCRIBED,
                                         error_code, error_msg)

    def test_change_state_with_no_config(self):
        self.ecc_server.selected_config = None
        with self.assertRaisesRegex(RuntimeError, 'Data source has no config associated with it.'):
            self._transition_test_helper('Describe', ECCServer.IDLE, ECCServer.DESCRIBED)


def check_data_link_xml_helper(testcase, datasource, link_xml):
    data_router = datasource.data_router

    testcase.assertEqual(link_xml.tag, 'DataLink')

    sender_nodes = link_xml.findall('DataSender')
    testcase.assertEqual(len(sender_nodes), 1, 'Must have only one sender node')
    testcase.assertEqual(sender_nodes[0].attrib, {'id': datasource.name})

    router_nodes = link_xml.findall('DataRouter')
    testcase.assertEqual(len(router_nodes), 1, 'Must have only one router node')

    testcase.assertEqual(
        router_nodes[0].attrib,
        {'name': data_router.name,
         'ipAddress': str(data_router.ip_address),
         'port': str(data_router.port),
         'type': data_router.connection_type
         }
    )


class DataSourceModelTestCase(TestCase):
    def setUp(self):
        self.name = 'CoBo[0]'
        self.experiment = Experiment.objects.create(
            name='Test',
        )
        self.ecc_server = ECCServer(
            name='ECC0',
            ip_address='123.456.789.0',
            experiment=self.experiment,
        )
        self.data_router = DataRouter(
            name='Router0',
            ip_address='111.111.111.111',
            connection_type=DataRouter.FDT,
            experiment=self.experiment,
        )
        self.datasource = DataSource(
            name=self.name,
            ecc_server=self.ecc_server,
            data_router=self.data_router,
        )
        self.ecc_server.save()
        self.data_router.save()
        self.datasource.save()

    def test_data_link_xml(self):
        xml = self.datasource.get_data_link_xml()
        check_data_link_xml_helper(self, self.datasource, xml)


class ExperimentModelTestCase(TestCase):
    def setUp(self):
        self.experiment = Experiment.objects.create(
            name='Test experiment',
        )

    def _create_run(self):
        return RunMetadata.objects.create(
            experiment=self.experiment,
            run_number=0,
            start_datetime=datetime(2016, 1, 1, 0, 0, 0),
            stop_datetime=datetime(2016, 1, 1, 1, 0, 0),
        )

    def test_latest_run_with_runs(self):
        run0 = self._create_run()
        self.assertEqual(self.experiment.latest_run, run0)

    def test_latest_run_without_runs(self):
        self.assertIsNone(self.experiment.latest_run)

    def test_is_running_when_running(self):
        run0 = self._create_run()
        run0.stop_datetime = None
        run0.save()
        self.assertTrue(self.experiment.is_running)

    def test_is_running_when_not_running(self):
        run0 = self._create_run()
        self.assertFalse(self.experiment.is_running)

    def test_is_running_without_runs(self):
        self.assertFalse(self.experiment.is_running)

    def test_next_run_number_with_runs(self):
        run0 = self._create_run()
        self.assertEqual(self.experiment.next_run_number, run0.run_number + 1)

    def test_next_run_number_without_runs(self):
        self.assertEqual(self.experiment.next_run_number, 0)

    def test_start_run(self):
        run0 = self._create_run()
        self.experiment.start_run()
        run1 = self.experiment.latest_run
        self.assertNotEqual(run1, run0)
        self.assertEqual(run1.run_number, run0.run_number + 1)

    def test_start_run_saves_config_name(self):
        ecc = ECCServer.objects.create(
            name='ECC',
            ip_address='123.123.123.123',
            experiment=self.experiment,
        )
        config = ConfigId.objects.create(
            ecc_server=ecc,
            describe='describe',
            prepare='prepare',
            configure='configure',
        )
        ecc.selected_config = config
        ecc.save()

        self.experiment.start_run()
        run = RunMetadata.objects.latest('start_datetime')
        self.assertEqual(run.config_name, config.configure)

    def test_start_run_only_considers_ecc_servers_from_this_experiment(self):
        ecc = ECCServer.objects.create(
            name='ECC',
            ip_address='123.123.123.123',
            experiment=self.experiment,
        )
        config = ConfigId.objects.create(
            ecc_server=ecc,
            describe='describe',
            prepare='prepare',
            configure='configure',
        )
        ecc.selected_config = config
        ecc.save()

        other_experiment = Experiment.objects.create(name='other')
        other_ecc = ECCServer.objects.create(
            name='other ecc',
            ip_address='123.123.123.123',
            experiment=other_experiment,
        )
        other_config = ConfigId.objects.create(
            ecc_server=other_ecc,
            describe='otherdescribe',
            prepare='otherprepare',
            configure='otherconfigure',
        )
        other_ecc.selected_config = other_config
        other_ecc.save()

        self.experiment.start_run()
        run = RunMetadata.objects.latest('start_datetime')
        self.assertEqual(run.config_name, config.configure)

    def test_start_run_when_running(self):
        self.experiment.start_run()
        with self.assertRaisesRegex(RuntimeError, 'Stop the current run before starting a new one'):
            self.experiment.start_run()

    def test_stop_run(self):
        run0 = self._create_run()
        run0.stop_datetime = None
        run0.save()
        self.experiment.stop_run()
        latest_run = self.experiment.latest_run
        self.assertEqual(latest_run, run0)
        self.assertIsNotNone(latest_run.stop_datetime)

    def test_stop_run_when_stopped(self):
        run0 = self._create_run()
        self.assertRaisesRegex(RuntimeError, 'Not running', self.experiment.stop_run)

    def test_change_active_experiment(self):
        self.experiment.is_active = True
        self.experiment.save()

        other_experiment = Experiment.objects.create(name='other')
        self.experiment.refresh_from_db()
        other_experiment.refresh_from_db()

        self.assertTrue(self.experiment.is_active)
        self.assertFalse(other_experiment.is_active)

        other_experiment.is_active = True
        other_experiment.save()
        self.experiment.refresh_from_db()
        other_experiment.refresh_from_db()

        self.assertFalse(self.experiment.is_active)
        self.assertTrue(other_experiment.is_active)


class RunMetadataModelTestCase(TestCase):
    def setUp(self):
        self.name = 'Test experiment'
        self.experiment = Experiment(
            name=self.name,
        )
        self.experiment.save()

        self.run0 = RunMetadata(experiment=self.experiment,
                                run_number=0,
                                start_datetime=datetime(year=2016,
                                                        month=1,
                                                        day=1,
                                                        hour=0,
                                                        minute=0,
                                                        second=0),
                                stop_datetime=datetime(year=2016,
                                                       month=1,
                                                       day=1,
                                                       hour=1,
                                                       minute=0,
                                                       second=0))

    def test_duration(self):
        expected = self.run0.stop_datetime - self.run0.start_datetime
        self.assertEqual(self.run0.duration, expected)

    def test_duration_while_running(self):
        self.run0.stop_datetime = None
        before = datetime.now() - self.run0.start_datetime
        dur = self.run0.duration
        after = datetime.now() - self.run0.start_datetime
        self.assertGreater(dur, before)
        self.assertLess(dur, after)


class MeasurementModelTestCase(TestCase):
    def setUp(self):
        self.experiment = Experiment.objects.create(
            name='Test experiment',
        )
        self.run = RunMetadata.objects.create(
            run_number=0,
            experiment=self.experiment,
            start_datetime=datetime(2016, 1, 1, 0, 0, 0),
            stop_datetime=datetime(2016, 1, 1, 1, 0, 0),
        )

    def _serialization_test_impl(self, obs_type, value):
        observable = Observable.objects.create(
            name='Test observable',
            value_type=obs_type,
            experiment=self.experiment,
        )
        measurement = Measurement(
            run_metadata=self.run,
            observable=observable,
        )

        if value is not None and not isinstance(value, measurement.python_type):
            with self.assertRaisesRegex(ValueError, r'Expected {}'.format(measurement.python_type)):
                measurement.value = value
            return
        else:
            measurement.value = value

        if value is None:
            self.assertIsNone(measurement.serialized_value)
        else:
            self.assertEqual(measurement.serialized_value, str(value))

        unpacked_value = measurement.value
        if value is None:
            self.assertIsNone(unpacked_value)
        else:
            self.assertEqual(unpacked_value, value)

    def test_serialization_with_integer(self):
        self._serialization_test_impl(Observable.INTEGER, 5)

    def test_serialization_with_float(self):
        self._serialization_test_impl(Observable.FLOAT, 4.5)

    def test_serialization_with_string(self):
        self._serialization_test_impl(Observable.STRING, 'test value')

    def test_stores_none(self):
        for value_type in (x[0] for x in Observable.value_type_choices):
            self._serialization_test_impl(value_type, None)

    def test_fails_when_type_mismatch(self):
        self._serialization_test_impl(Observable.FLOAT, 'string')
        self._serialization_test_impl(Observable.STRING, 4)
        self._serialization_test_impl(Observable.INTEGER, 4.5)
