from django.test import TestCase
from django.conf import settings
from django.contrib.auth.models import User
from unittest.mock import patch
from .utilities import FakeResponseState
from ..models import DataRouter, DataSource, ConfigId, Experiment, RunMetadata
from ..models import ECCError
import xml.etree.ElementTree as ET
import os
from itertools import permutations, product
from datetime import datetime
import pytz


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


class DataRouterModelTestCase(TestCase):
    def setUp(self):
        self.name = 'dataRouterName'
        self.ip_address = '123.456.78.9'
        self.port = '1234'
        self.datarouter = DataRouter(name=self.name,
                                     ip_address=self.ip_address,
                                     port=self.port)

    def test_str(self):
        s = str(self.datarouter)
        self.assertEqual(s, self.name)


class DataSourceModelTestCase(TestCase):
    def setUp(self):
        self.name = 'CoBo[0]'
        self.ecc_ip_address = '123.45.67.8'
        self.ecc_port = '1234'
        self.datarouter = DataRouter(name='dataRouter0',
                                     ip_address='123.456.78.9',
                                     port='1111')
        self.selected_config = ConfigId(describe='describe',
                                        prepare='prepare',
                                        configure='configure')
        self.datasource = DataSource(name=self.name,
                                     ecc_ip_address=self.ecc_ip_address,
                                     ecc_port=self.ecc_port,
                                     data_router=self.datarouter,
                                     selected_config=self.selected_config)
        self.datarouter.save()
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
        self.assertEqual(router_nodes[0].attrib, {'name': self.datarouter.name,
                                                  'ipAddress': self.datarouter.ip_address,
                                                  'port': self.datarouter.port,
                                                  'type': self.datarouter.type})

    def test_ecc_url(self):
        ecc_url = self.datasource.ecc_url
        expected = 'http://{}:{}/'.format(self.ecc_ip_address, self.ecc_port)
        self.assertEqual(ecc_url, expected)

    def test_get_soap_client(self):
        with patch('attpcdaq.daq.models.SoapClient') as mock_client:
            instance = mock_client.return_value
            self.datasource._get_soap_client()

            wsdl = os.path.join(settings.BASE_DIR, 'attpcdaq', 'daq', 'ecc.wsdl')
            mock_client.assert_called_once_with(wsdl)
            instance.set_address.assert_called_once_with('ecc', 'ecc', self.datasource.ecc_url)

    @patch('attpcdaq.daq.models.SoapClient')
    def test_get_transition_too_many_steps(self, mock_client):
        mock_instance = mock_client()
        for initial_state, final_state in permutations(DataSource.STATE_DICT.keys(), 2):
            if final_state - initial_state not in (1, -1):
                self.assertRaisesRegex(ValueError, 'Can only transition one step at a time\.',
                                       self.datasource._get_transition, mock_instance,
                                       initial_state, final_state)

    @patch('attpcdaq.daq.models.SoapClient')
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

        with patch('attpcdaq.daq.models.SoapClient') as mock_client:
            instance = mock_client.return_value
            instance.service.GetConfigIDs.side_effect = return_side_effect

            self.datasource.refresh_configs()

            instance.service.GetConfigIDs.assert_called_once_with()

        for config in configs:
            self.assertTrue(ConfigId.objects.filter(describe=config.describe,
                                                    prepare=config.prepare,
                                                    configure=config.configure).exists())

    def test_refresh_state(self):
        for (state, trans) in product(DataSource.STATE_DICT.keys(), [False, True]):
            with patch('attpcdaq.daq.models.SoapClient') as mock_client:
                mock_inst = mock_client.return_value
                mock_inst.service.GetState.return_value = \
                    FakeResponseState(state=state, trans=trans)

                self.datasource.refresh_state()

                mock_inst.service.GetState.assert_called_once_with()

            self.assertEqual(self.datasource.state, state)
            self.assertEqual(self.datasource.is_transitioning, trans)

    def _transition_test_helper(self, trans_func_name, initial_state, final_state,
                                error_code=0, error_msg=""):
        with patch('attpcdaq.daq.models.SoapClient') as mock_client:
            self.datasource.state = initial_state
            self.datasource.is_transitioning = False

            mock_instance = mock_client.return_value
            mock_trans_func = getattr(mock_instance.service, trans_func_name)
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

    def test_change_state_with_no_data_router(self):
        self.datasource.data_router = None
        with self.assertRaisesRegex(RuntimeError, 'Data source has no data router associated with it.'):
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
                                                        second=0,
                                                        tzinfo=pytz.utc),
                                stop_datetime=datetime(year=2016,
                                                       month=1,
                                                       day=1,
                                                       hour=1,
                                                       minute=0,
                                                       second=0,
                                                       tzinfo=pytz.utc))

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
                                                        second=0,
                                                        tzinfo=pytz.utc),
                                stop_datetime=datetime(year=2016,
                                                       month=1,
                                                       day=1,
                                                       hour=1,
                                                       minute=0,
                                                       second=0,
                                                       tzinfo=pytz.utc))

    def test_duration(self):
        expected = str(self.run0.stop_datetime - self.run0.start_datetime)
        self.assertEqual(self.run0.duration, expected)
