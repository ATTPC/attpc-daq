from django.test import TestCase
from django.conf import settings
from django.contrib.auth.models import User
from unittest.mock import patch
from .utilities import FakeResponseState, FakeResponseText
from ..models import DataSource, ConfigId, Experiment, RunMetadata
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


class DataSourceModelTestCase(TestCase):
    def setUp(self):
        self.name = 'CoBo[0]'
        self.ecc_ip_address = '123.45.67.8'
        self.ecc_port = '1234'
        self.data_router_ip_address = '123.45.67.89'
        self.data_router_port = 46005
        self.data_router_type = DataSource.TCP
        self.selected_config = ConfigId(describe='describe',
                                        prepare='prepare',
                                        configure='configure')
        self.datasource = DataSource(name=self.name,
                                     ecc_ip_address=self.ecc_ip_address,
                                     ecc_port=self.ecc_port,
                                     data_router_ip_address=self.data_router_ip_address,
                                     data_router_port=self.data_router_port,
                                     data_router_type=self.data_router_type,
                                     selected_config=self.selected_config)
        self.selected_config.save()
        self.datasource.save()

    def test_str(self):
        s = str(self.datasource)
        self.assertEqual(s, self.name)

    def test_get_data_link_xml(self):
        xml_string = self.datasource.get_data_link_xml()
        root = ET.fromstring(xml_string)

        self.assertEqual(root.tag, 'DataLinkSet')
        self.assertEqual(len(root), 1, 'Root node should have one child')

        dl_node = root[0]
        self.assertEqual(dl_node.tag, 'DataLink')

        sender_nodes = dl_node.findall('DataSender')
        self.assertEqual(len(sender_nodes), 1, 'Must have only one sender node')
        self.assertEqual(sender_nodes[0].attrib, {'id': self.datasource.name})

        router_nodes = dl_node.findall('DataRouter')
        self.assertEqual(len(router_nodes), 1, 'Must have only one router node')

        self.assertEqual(router_nodes[0].attrib, {'name': self.datasource.data_router_name,
                                                  'ipAddress': str(self.data_router_ip_address),
                                                  'port': str(self.data_router_port),
                                                  'type': self.data_router_type})

    def test_ecc_url(self):
        ecc_url = self.datasource.ecc_url
        expected = 'http://{}:{}/'.format(self.ecc_ip_address, self.ecc_port)
        self.assertEqual(ecc_url, expected)

    @patch('attpcdaq.daq.models.EccClient')
    def test_get_transition_too_many_steps(self, mock_client):
        mock_instance = mock_client()
        for initial_state, final_state in permutations(DataSource.STATE_DICT.keys(), 2):
            if final_state - initial_state not in (1, -1):
                self.assertRaisesRegex(ValueError, 'Can only transition one step at a time\.',
                                       self.datasource._get_transition, mock_instance,
                                       initial_state, final_state)

    @patch('attpcdaq.daq.models.EccClient')
    def test_get_transition_same_state(self, mock_client):
        mock_instance = mock_client()
        for state in DataSource.STATE_DICT.keys():
            self.assertRaisesRegex(ValueError, 'No transition needed.', self.datasource._get_transition,
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

            self.datasource.refresh_configs()

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

        self.datasource.refresh_configs()
        self.datasource.refresh_configs()  # Call a second time to see if duplication occurs

        self.assertEqual(len(self.datasource.configid_set.all()), len(configs))

    @patch('attpcdaq.daq.models.EccClient')
    def test_refresh_configs_removes_outdated(self, mock_client):
        config_names = ['A', 'B', 'C']
        configs = [ConfigId(describe=a, prepare=b, configure=c)
                   for a, b, c in permutations(config_names, 3)]
        configs_xml = '<ConfigIdList>' + ''.join((c.as_xml() for c in configs)) + '</ConfigIdList>'

        mock_inst = mock_client.return_value
        mock_inst.GetConfigIDs.return_value = FakeResponseText(text=configs_xml)

        self.datasource.refresh_configs()  # Get the initial list

        # Remove a config and update the mock response
        removed_config = configs[0]
        del configs[0]
        configs_xml = '<ConfigIdList>' + ''.join((c.as_xml() for c in configs)) + '</ConfigIdList>'
        mock_inst.GetConfigIDs.return_value = FakeResponseText(text=configs_xml)

        self.datasource.refresh_configs()  # Now pull in the updated list

        self.assertFalse(self.datasource.configid_set.filter(describe=removed_config.describe,
                                                             prepare=removed_config.prepare,
                                                             configure=removed_config.configure).exists(),
                         msg='Removed config was still present in database.')

    def test_refresh_state(self):
        for (state, trans) in product(DataSource.STATE_DICT.keys(), [False, True]):
            with patch('attpcdaq.daq.models.EccClient') as mock_client:
                mock_inst = mock_client.return_value
                mock_inst.GetState.return_value = \
                    FakeResponseState(state=state, trans=trans)

                self.datasource.refresh_state()

                mock_inst.GetState.assert_called_once_with()

            self.assertEqual(self.datasource.state, state)
            self.assertEqual(self.datasource.is_transitioning, trans)

    def _transition_test_helper(self, trans_func_name, initial_state, final_state,
                                error_code=0, error_msg=""):
        with patch('attpcdaq.daq.models.EccClient') as mock_client:
            self.datasource.state = initial_state
            self.datasource.is_transitioning = False

            mock_instance = mock_client.return_value
            mock_trans_func = getattr(mock_instance, trans_func_name)
            mock_trans_func.return_value = FakeTransitionResult(error_code, error_msg)

            self.datasource.change_state(final_state)

            config_xml = self.datasource.selected_config.as_xml()
            datalink_xml = self.datasource.get_data_link_xml()
            mock_trans_func.assert_called_once_with(config_xml, datalink_xml)

            self.assertTrue(self.datasource.is_transitioning)

    def test_change_state(self):
        self._transition_test_helper('Describe', DataSource.IDLE, DataSource.DESCRIBED)
        self._transition_test_helper('Undo', DataSource.DESCRIBED, DataSource.IDLE)

        self._transition_test_helper('Prepare', DataSource.DESCRIBED, DataSource.PREPARED)
        self._transition_test_helper('Undo', DataSource.PREPARED, DataSource.DESCRIBED)

        self._transition_test_helper('Configure', DataSource.PREPARED, DataSource.READY)
        self._transition_test_helper('Breakup', DataSource.READY, DataSource.PREPARED)

        self._transition_test_helper('Start', DataSource.READY, DataSource.RUNNING)
        self._transition_test_helper('Stop', DataSource.RUNNING, DataSource.READY)

    def test_change_state_with_error(self):
        error_code = 1
        error_msg = 'An error occurred'

        with self.assertRaisesRegex(ECCError, '.*' + error_msg):
            self._transition_test_helper('Describe', DataSource.IDLE, DataSource.DESCRIBED,
                                         error_code, error_msg)

    def test_change_state_with_no_config(self):
        self.datasource.selected_config = None
        with self.assertRaisesRegex(RuntimeError, 'Data source has no config associated with it.'):
            self._transition_test_helper('Describe', DataSource.IDLE, DataSource.DESCRIBED)


class ExperimentModelTestCase(TestCase):
    def setUp(self):
        self.user = User(username='test', password='test1234')
        self.user.save()
        self.name = 'Test experiment'
        self.target_run_duration = 1000
        self.experiment = Experiment(user=self.user,
                                     name=self.name,
                                     target_run_duration=self.target_run_duration)
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

    def test_latest_run_with_runs(self):
        self.run0.save()
        self.assertEqual(self.experiment.latest_run, self.run0)

    def test_latest_run_without_runs(self):
        self.assertIsNone(self.experiment.latest_run)

    def test_is_running_when_running(self):
        self.run0.stop_datetime = None
        self.run0.save()
        self.assertTrue(self.experiment.is_running)

    def test_is_running_when_not_running(self):
        self.run0.save()
        self.assertFalse(self.experiment.is_running)

    def test_is_running_without_runs(self):
        self.assertFalse(self.experiment.is_running)

    def test_next_run_number_with_runs(self):
        self.run0.save()
        self.assertEqual(self.experiment.next_run_number, self.run0.run_number + 1)

    def test_next_run_number_without_runs(self):
        self.assertEqual(self.experiment.next_run_number, 0)

    def test_start_run(self):
        self.run0.save()
        self.experiment.start_run()
        run = self.experiment.latest_run
        self.assertNotEqual(run, self.run0)
        self.assertEqual(run.run_number, self.run0.run_number + 1)

    def test_start_run_when_running(self):
        self.experiment.start_run()
        self.assertRaisesRegex(RuntimeError, 'Stop the current run before starting a new one',
                               self.experiment.start_run)

    def test_stop_run(self):
        self.run0.stop_datetime = None
        self.run0.save()
        self.experiment.stop_run()
        run = self.experiment.latest_run
        self.assertEqual(run, self.run0)
        self.assertIsNotNone(run.stop_datetime)

    def test_stop_run_when_stopped(self):
        self.run0.save()
        self.assertRaisesRegex(RuntimeError, 'Not running', self.experiment.stop_run)


class RunMetadataModelTestCase(TestCase):
    def setUp(self):
        self.user = User(username='test', password='test1234')
        self.user.save()
        self.name = 'Test experiment'
        self.target_run_duration = 1000
        self.experiment = Experiment(user=self.user,
                                     name=self.name,
                                     target_run_duration=self.target_run_duration)
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