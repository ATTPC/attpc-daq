"""Unit tests for Django forms"""

from django.test import TestCase
from django import forms

from ..forms import RunMetadataForm, DataSourceForm, ECCServerForm, DataRouterForm, ConfigSelectionForm, ObservableForm
from ..models import RunMetadata, Observable, Measurement, Experiment, DataSource, ECCServer, DataRouter


class TestModelFormFieldsMixin(object):
    def get_excluded_fields(self):
        return set()

    def get_expected_fields(self):
        all_fields = {f.name for f in self.model._meta.get_fields(include_parents=False)
                      if not f.auto_created}
        return all_fields - self.get_excluded_fields()

    def test_has_all_fields_in_model(self):
        expected_field_names = self.get_expected_fields()
        form_field_names = set(self.form.Meta.fields)
        self.assertEqual(form_field_names, expected_field_names)


class DataSourceFormTestCase(TestModelFormFieldsMixin, TestCase):
    def setUp(self):
        self.model = DataSource
        self.form = DataSourceForm


class ECCServerFormTestCase(TestModelFormFieldsMixin, TestCase):
    def setUp(self):
        self.model = ECCServer
        self.form = ECCServerForm

    def get_excluded_fields(self):
        return {'is_online', 'state', 'selected_config', 'is_transitioning', 'experiment'}


class DataRouterFormTestCase(TestModelFormFieldsMixin, TestCase):
    def setUp(self):
        self.model = DataRouter
        self.form = DataRouterForm

    def get_excluded_fields(self):
        return {'is_online', 'staging_directory_is_clean', 'experiment'}


class ConfigSelectionFormTestCase(TestModelFormFieldsMixin, TestCase):
    def setUp(self):
        self.model = ECCServer
        self.form = ConfigSelectionForm

    def get_expected_fields(self):
        return {'selected_config'}


class RunMetadataFormTestCase(TestModelFormFieldsMixin, TestCase):
    def setUp(self):
        self.model = RunMetadata
        self.form = RunMetadataForm

        self.experiment = Experiment.objects.create(
            name='Test experiment',
        )
        self.string_observable = Observable.objects.create(
            name='string observable',
            value_type=Observable.STRING,
            experiment=self.experiment,
        )
        self.int_observable = Observable.objects.create(
            name='int observable',
            value_type=Observable.INTEGER,
            experiment=self.experiment,
        )
        self.float_observable = Observable.objects.create(
            name='float observable',
            value_type=Observable.FLOAT,
            experiment=self.experiment,
        )
        self.observables = [self.string_observable, self.int_observable, self.float_observable]

        self.observable_type_map = {
            Observable.FLOAT: float,
            Observable.INTEGER: int,
            Observable.STRING: str,
        }

        self.run = RunMetadata.objects.create(
            run_number=0,
            experiment=self.experiment,
            run_class=RunMetadata.TESTING,
        )

    def get_excluded_fields(self):
        return {'experiment'}

    def test_has_fields_for_observables(self):
        form = RunMetadataForm(instance=self.run)

        field_type_map = {
            Observable.INTEGER: forms.IntegerField,
            Observable.FLOAT: forms.FloatField,
            Observable.STRING: forms.CharField,
        }

        for obs in self.observables:
            self.assertIn(obs.name, form.fields.keys())
            field = form.fields[obs.name]
            self.assertIsInstance(field, field_type_map[obs.value_type])

    def test_measurements_are_saved(self):
        data = {o.name: self.observable_type_map[o.value_type](5) for o in self.observables}
        for field in self.get_expected_fields():
            data[field] = getattr(self.run, field)

        form = RunMetadataForm(data=data, instance=self.run)
        if form.is_valid():
            form.save()
        else:
            self.fail('Form was not valid: {}'.format(form.errors.as_data()))

        measurements = Measurement.objects.all().select_related('observable')
        self.assertEqual(len(measurements), len(self.observables))

        for measurement in measurements:
            self.assertEqual(measurement.value, data[measurement.observable.name])


class ObservableFormTestCase(TestModelFormFieldsMixin, TestCase):
    def setUp(self):
        self.model = Observable
        self.form = ObservableForm

    def get_excluded_fields(self):
        return {'experiment', 'order'}
