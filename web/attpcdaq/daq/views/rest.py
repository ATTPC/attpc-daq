from ..models import DataRouter, ECCServer, ConfigId, RunMetadata, Experiment, ECCError
from ..serializers import DataRouterSerializer, ECCServerSerializer, ConfigIdSerializer, RunMetadataSerializer, ExperimentSerializer
from ..workertasks import WorkerInterface
from ..tasks import eccserver_change_state_task, organize_files_all_task
from .helpers import calculate_overall_state

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import detail_route, list_route

from django.shortcuts import get_object_or_404

import logging
logger = logging.getLogger(__name__)


class DataRouterViewSet(viewsets.ModelViewSet):

    queryset = DataRouter.objects.all()
    serializer_class = DataRouterSerializer

    @detail_route(methods=['get'])
    def log_file(self, request, pk):
        data_router = self.get_object()
        with WorkerInterface(data_router.ip_address) as wint:
            log_content = wint.tail_file(data_router.log_path)

        return Response({'content': log_content})



class ECCServerViewSet(viewsets.ModelViewSet):
    queryset = ECCServer.objects.all()
    serializer_class = ECCServerSerializer

    @detail_route(methods=['get'])
    def log_file(self, request, pk):
        ecc_server = self.get_object()
        with WorkerInterface(ecc_server.ip_address) as wint:
            log_content = wint.tail_file(ecc_server.log_path)

        return Response({'content': log_content})

    @staticmethod
    def _get_target_state_from_transition(current_state, transition):
        if transition == 'describe':
            return ECCServer.DESCRIBED
        elif transition == 'prepare':
            return ECCServer.PREPARED
        elif transition == 'configure':
            return ECCServer.READY
        elif transition == 'start':
            return ECCServer.RUNNING
        elif transition == 'stop':
            return ECCServer.READY
        elif transition == 'reset':
            return max(current_state - 1, ECCServer.IDLE)
        else:
            raise ValueError('Invalid transition requested: %s', transition)


    @detail_route(methods=['post'], url_path=r'(?P<transition>describe|prepare|configure|start|stop|reset)')
    def change_state(self, request, pk, transition):
        try:
            ecc_server = self.get_object()

            try:
                target_state = self._get_target_state_from_transition(ecc_server.state, transition)
            except ValueError:
                logger.exception('Failed to get target state.')
                return Response({'success': False}, status=status.HTTP_400_BAD_REQUEST)

            # Request the transition
            ecc_server.is_transitioning = True
            ecc_server.save()
            eccserver_change_state_task.delay(ecc_server.pk, target_state)

        except Exception:
            logger.exception('Failed to request state transition')
            return Response({'success': False}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        else:
            return Response({
                'success': True,
                'is_transitioning': ecc_server.is_transitioning,
                'get_state_display': ecc_server.get_state_display(),
            })

    @list_route(methods=['post'], url_path=r'(?P<transition>describe|prepare|configure|start|stop|reset)')
    def change_state_all(self, request, transition):
        current_state, current_state_name = calculate_overall_state()
        if current_state is None:
            logger.error('Overall state is inconsistent. Fix this before changing state of all servers.')
            return Response({'success': False}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_state = self._get_target_state_from_transition(current_state, transition)
        except ValueError:
            logger.exception('Failed to get target state.')
            return Response({'success': False}, status=status.HTTP_400_BAD_REQUEST)

        # Check if data routers are ready
        if target_state == ECCServer.RUNNING:
            daq_not_ready = DataRouter.objects.exclude(staging_directory_is_clean=True).exists()
            if daq_not_ready:
                logger.error('Data routers are not ready')
                return Response({'success': False}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        for ecc_server in ECCServer.objects.all():
            try:
                ecc_server.is_transitioning = True
                ecc_server.save()
                eccserver_change_state_task.delay(ecc_server.pk, target_state)
            except (ECCError, ValueError):
                logger.exception('Failed to submit change_state task for ECC server %s', ecc_server.name)

        experiment = get_object_or_404(Experiment, user=request.user)

        is_starting = target_state == ECCServer.RUNNING and not experiment.is_running
        is_stopping = target_state == ECCServer.READY and experiment.is_running

        if is_starting:
            experiment.start_run()
        elif is_stopping:
            experiment.stop_run()
            run_number = experiment.latest_run.run_number
            organize_files_all_task.delay(experiment.name, run_number)

        return Response({'success': True})

    @list_route(methods=['get'])
    def overall_state(self, request):
        overall_state, overall_state_name = calculate_overall_state()
        return Response({
            'success': True,
            'overall_state': overall_state,
            'overall_state_name': overall_state_name,
        })


class ConfigIdViewSet(viewsets.ModelViewSet):
    queryset = ConfigId.objects.all()
    serializer_class = ConfigIdSerializer


class RunMetadataViewSet(viewsets.ModelViewSet):
    serializer_class = RunMetadataSerializer

    def get_queryset(self):
        experiment = Experiment.objects.get(user=self.request.user)
        return RunMetadata.objects.filter(experiment=experiment)


class ExperimentViewSet(viewsets.ModelViewSet):
    serializer_class = ExperimentSerializer

    def get_queryset(self):
        return Experiment.objects.filter(user=self.request.user)
