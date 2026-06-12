"""gRPC servicer fixture (DEC-060) — the provider (HANDLES) side.

Implements two of the three proto rpcs; RecordRoute is left unimplemented (a
spec-only endpoint, surfaced honestly via the .proto with no servicer).
"""

import route_guide_pb2_grpc


class RouteGuideServicer(route_guide_pb2_grpc.RouteGuideServicer):
    def GetFeature(self, request, context):
        return Feature()

    def ListFeatures(self, request, context):
        yield Feature()
