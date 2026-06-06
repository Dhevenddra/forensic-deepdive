// Configured-client frontend (DEC-056 acceptance fixture, the SupersetClient shape).
// Exercises the configured-client consumer extractor: <Client>.get/post/delete({ endpoint })
// and <Client>.request({ method, endpoint }), with endpoint/url/path keys, a
// templated endpoint (INFERRED), and an axios receiver that must be skipped
// (the fetch/axios extractor owns it).
import { SupersetClient } from '@superset-ui/core';
import axios from 'axios';

export function fetchChartData(id: string) {
  // templated endpoint → INFERRED; joins ChartRestApi.data
  return SupersetClient.get({ endpoint: `/api/v1/chart/${id}/data/` });
}

export function createChart(payload: object) {
  // literal endpoint → EXTRACTED; joins ChartRestApi.bulk_create
  return SupersetClient.post({ endpoint: '/api/v1/chart/', jsonPayload: payload });
}

export function exportDashboard() {
  // .request({ method, endpoint }) → verb from the method key; joins DashboardRestApi.export
  return SupersetClient.request({ method: 'GET', endpoint: '/api/v1/dashboard/export/' });
}

export function listTags() {
  // 'url' key variant; no matching provider → CALLS_ENDPOINT only
  return SupersetClient.get({ url: '/api/v1/tag/' });
}

export function legacyReport() {
  // 'path' key variant + numeric segment → INFERRED; no matching provider
  return SupersetClient.delete({ path: '/api/v1/report/9' });
}

export function dynamicEndpoint(ep: string) {
  // fully dynamic endpoint (bare variable) → dropped, no stable contract_id
  return SupersetClient.get({ endpoint: ep });
}

export function viaAxios() {
  // axios receiver is owned by the fetch/axios extractor → configured_client skips it
  return axios.get({ url: '/api/v1/owned/' });
}
