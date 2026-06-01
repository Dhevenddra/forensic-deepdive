import { HttpClient } from '@angular/common/http';

export class UserApi {
  constructor(private http: HttpClient) {}

  loadUser(id: string) {
    return this.http.get(`/api/users/${id}`);
  }

  addUser(body: unknown) {
    return this.http.post('/api/users', body);
  }
}
