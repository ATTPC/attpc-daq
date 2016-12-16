from ..models import DataRouter, ECCServer, ConfigId
from ..serializers import DataRouterSerializer, ECCServerSerializer, ConfigIdSerializer
from ..workertasks import WorkerInterface

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import detail_route


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


class ConfigIdViewSet(viewsets.ModelViewSet):
    queryset = ConfigId.objects.all()
    serializer_class = ConfigIdSerializer
