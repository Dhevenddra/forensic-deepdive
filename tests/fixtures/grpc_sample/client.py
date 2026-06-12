"""gRPC stub-client fixture (DEC-060) — the consumer (CALLS_ENDPOINT) side."""

import route_guide_pb2_grpc


def fetch_feature(channel, point):
    stub = route_guide_pb2_grpc.RouteGuideStub(channel)
    feature = stub.GetFeature(point)
    return feature


def list_all(channel, rect):
    stub = route_guide_pb2_grpc.RouteGuideStub(channel)
    return stub.ListFeatures(rect)
