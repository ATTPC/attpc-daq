from ..models import DataRouter, ECCServer, ConfigId
from ..serializers import DataRouterSerializer, ECCServerSerializer, ConfigIdSerializer
from ..workertasks import WorkerInterface
from ..tasks import eccserver_change_state_task

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import detail_route

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

    @detail_route(methods=['post'], url_path=r'(?P<transition>describe|prepare|configure|start|stop|reset)')
    def change_state(self, request, pk, transition):
        try:
            ecc_server = self.get_object()

            if transition == 'describe':
                target_state = ECCServer.DESCRIBED
            elif transition == 'prepare':
                target_state = ECCServer.PREPARED
            elif transition == 'configure':
                target_state = ECCServer.READY
            elif transition == 'start':
                target_state = ECCServer.RUNNING
            elif transition == 'stop':
                target_state = ECCServer.READY
            elif transition == 'reset':
                target_state = max(ecc_server.state - 1, ECCServer.IDLE)
            else:
                logger.error('Invalid transition requested: %s', transition)
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


class ConfigIdViewSet(viewsets.ModelViewSet):
    queryset = ConfigId.objects.all()
    serializer_class = ConfigIdSerializer
