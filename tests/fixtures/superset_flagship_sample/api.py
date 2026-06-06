"""Flask-AppBuilder backend (DEC-056 acceptance fixture, the Superset shape).

Exercises the FAB provider extractor: a ``ModelRestApi`` with ``resource_name``
(EXTRACTED prefix), a ``BaseApi`` with an explicit ``route_base`` (EXTRACTED), a
``ModelRestApi`` with no base attr (class-name convention → INFERRED), a bare
``@expose`` defaulting to GET, and a ``ModelView`` that must be ignored (HTML
view, not an ``/api/v1`` join target).
"""

from flask_appbuilder import ModelView
from flask_appbuilder.api import BaseApi, ModelRestApi, expose


class ChartRestApi(ModelRestApi):
    resource_name = "chart"
    version = "v1"

    @expose("/<pk>/data/", methods=["GET"])
    def data(self, pk):
        return {"pk": pk}

    @expose("/", methods=["POST"])
    def bulk_create(self):
        return {}


class DashboardRestApi(BaseApi):
    route_base = "/api/v1/dashboard"

    @expose("/export/")  # no methods= → GET default
    def export(self):
        return {}


class LogRestApi(ModelRestApi):
    # no resource_name / route_base → FAB class-name convention (INFERRED prefix)

    @expose("/recent", methods=["GET"])
    def recent(self):
        return {}


class WidgetView(ModelView):
    # NOT a FAB API base → ignored (its @expose is an HTML route, no /api/v1).
    @expose("/list/")
    def widget_list(self):
        return {}
